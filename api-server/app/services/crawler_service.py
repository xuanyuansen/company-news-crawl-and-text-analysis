import subprocess
import os
import signal
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.core.config import settings

class CrawlerService:
    def __init__(self):
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.task_history: List[Dict[str, Any]] = []
        
        # Site configurations matching the project config
        self.sites = [
            {"name": "east_money", "display_name": "东方财富网", "db_name": "east_money_news", "enabled": True},
            {"name": "jrj", "display_name": "金融界", "db_name": "jrj_news", "enabled": True},
            {"name": "nbd", "display_name": "每经网", "db_name": "nbd_news", "enabled": True},
            {"name": "net_ease", "display_name": "网易财经", "db_name": "net_ease_news", "enabled": True},
            {"name": "shanghai", "display_name": "上海证券报", "db_name": "shanghai_cn_stock_news", "enabled": True},
            {"name": "zhong_jin", "display_name": "中金在线", "db_name": "zhong_jin_stock_news_db", "enabled": True},
            {"name": "jqka", "display_name": "同花顺", "db_name": "jqka", "enabled": True},
            {"name": "mei_tong", "display_name": "美通社", "db_name": "mei_tong_she_news", "enabled": True},
        ]
    
    def get_sites(self) -> List[Dict[str, Any]]:
        """Get all site configurations"""
        # Add last run info from history
        for site in self.sites:
            history = [h for h in self.task_history if h["site"] == site["name"]]
            if history:
                site["last_run"] = history[-1]["start_time"]
        return self.sites
    
    def start_crawler(self, site: str, mode: str = "one_day") -> Dict[str, Any]:
        """Start a crawler for a specific site"""
        if site in self.active_processes:
            return {"status": "already_running", "pid": self.active_processes[site].pid}
        
        try:
            # Build command
            if mode == "one_day":
                cmd = [
                    "python", "run_scrapy_one_day.py",
                    "-s", "spider"
                ]
            elif mode == "full":
                cmd = [
                    "python", "run_scripy_spider.py",
                    site if site != "all" else "all"
                ]
            else:
                return {"status": "error", "message": f"Unknown mode: {mode}"}
            
            # Start process
            process = subprocess.Popen(
                cmd,
                cwd=settings.SRC_PATH,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            self.active_processes[site] = process
            
            # Record in history
            self.task_history.append({
                "id": f"{site}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "site": site,
                "mode": mode,
                "start_time": datetime.now().isoformat(),
                "pid": process.pid,
                "status": "running"
            })
            
            return {
                "status": "started",
                "pid": process.pid,
                "site": site,
                "mode": mode
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def stop_crawler(self, site: str) -> Dict[str, Any]:
        """Stop a running crawler"""
        if site not in self.active_processes:
            return {"status": "not_running"}
        
        try:
            process = self.active_processes[site]
            
            # Kill process group
            if hasattr(os, 'killpg'):
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            else:
                process.terminate()
            
            del self.active_processes[site]
            
            # Update history
            for task in reversed(self.task_history):
                if task["site"] == site and task["status"] == "running":
                    task["status"] = "stopped"
                    task["end_time"] = datetime.now().isoformat()
                    break
            
            return {"status": "stopped", "site": site}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_status(self) -> Dict[str, List[str]]:
        """Get current crawler status"""
        # Clean up finished processes
        finished = []
        for site, process in list(self.active_processes.items()):
            if process.poll() is not None:
                finished.append(site)
                del self.active_processes[site]
                
                # Update history
                for task in reversed(self.task_history):
                    if task["site"] == site and task["status"] == "running":
                        task["status"] = "completed" if process.returncode == 0 else "failed"
                        task["end_time"] = datetime.now().isoformat()
                        break
        
        return {
            "active": list(self.active_processes.keys()),
            "queue": [],  # Could implement queue if needed
            "finished": finished
        }
    
    def get_recent_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent crawler tasks"""
        # Update status of running tasks
        self.get_status()
        
        # Calculate progress for running tasks
        tasks = []
        for task in reversed(self.task_history[-limit:]):
            task_copy = task.copy()
            if task["status"] == "running":
                # Simulate progress based on time
                start = datetime.fromisoformat(task["start_time"])
                elapsed = (datetime.now() - start).total_seconds()
                # Assume 5 minutes for a typical crawl
                progress = min(int(elapsed / 300 * 100), 95)
                task_copy["progress"] = progress
            else:
                task_copy["progress"] = 100
            tasks.append(task_copy)
        
        return tasks
    
    def generate_report(self, days: int = 3) -> Dict[str, Any]:
        """Generate news report"""
        try:
            cmd = [
                "python", "run_scrapy_one_day.py",
                "-r", str(days)
            ]
            
            process = subprocess.Popen(
                cmd,
                cwd=settings.SRC_PATH,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = process.communicate(timeout=300)
            
            if process.returncode == 0:
                return {
                    "status": "success",
                    "message": "Report generated successfully",
                    "output": stdout.decode('utf-8', errors='ignore')
                }
            else:
                return {
                    "status": "error",
                    "message": stderr.decode('utf-8', errors='ignore')
                }
                
        except subprocess.TimeoutExpired:
            process.kill()
            return {"status": "error", "message": "Report generation timed out"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

# Singleton instance
crawler_service = CrawlerService()
