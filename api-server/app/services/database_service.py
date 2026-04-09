import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'src'))

try:
    from Utils.database import Database
    from Utils import config as project_config
except ImportError as e:
    print(f"Warning: Could not import project modules: {e}")
    Database = None
    project_config = None

class DatabaseService:
    def __init__(self):
        self.db = None
        self._connected = False
        self._connect()
    
    def _connect(self):
        """Connect to MongoDB"""
        try:
            if Database:
                self.db = Database()
                self._connected = True
            else:
                # Fallback: use pymongo directly
                from pymongo import MongoClient
                self.client = MongoClient("localhost", 27017, serverSelectionTimeoutMS=5000)
                self._connected = True
        except Exception as e:
            print(f"Database connection error: {e}")
            self._connected = False
    
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self._connected
    
    def get_database_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all databases"""
        if not self._connected:
            return []
        
        try:
            if Database:
                # Use project Database class
                client = self.db.conn
            else:
                client = self.client
            
            databases = []
            news_dbs = [
                "east_money_news",
                "jrj_news", 
                "nbd_news",
                "net_ease_news",
                "shanghai_cn_stock_news",
                "zhong_jin_stock_news_db",
                "mei_tong_she_news",
                "jqka",
                "stock",
                "stock_specific_news"
            ]
            
            for db_name in news_dbs:
                try:
                    db = client[db_name]
                    collections = db.list_collection_names()
                    total_docs = 0
                    for col_name in collections:
                        total_docs += db[col_name].estimated_document_count()
                    
                    databases.append({
                        "name": db_name,
                        "collections": len(collections),
                        "documents": total_docs,
                        "size": "-"  # Would need db.stats() for size
                    })
                except Exception:
                    continue
            
            return databases
        except Exception as e:
            print(f"Error getting database stats: {e}")
            return []
    
    def get_collections(self, db_name: str) -> List[Dict[str, Any]]:
        """Get collections for a database"""
        if not self._connected:
            return []
        
        try:
            if Database:
                client = self.db.conn
            else:
                client = self.client
            
            db = client[db_name]
            collections = []
            
            for col_name in db.list_collection_names():
                try:
                    count = db[col_name].estimated_document_count()
                    collections.append({
                        "name": col_name,
                        "count": count,
                        "size": "-"
                    })
                except Exception:
                    continue
            
            return collections
        except Exception as e:
            print(f"Error getting collections: {e}")
            return []
    
    def get_documents(self, db_name: str, collection: str, limit: int = 100, skip: int = 0) -> Dict[str, Any]:
        """Get documents from a collection"""
        if not self._connected:
            return {"documents": [], "total": 0}
        
        try:
            if Database:
                client = self.db.conn
            else:
                client = self.client
            
            db = client[db_name]
            col = db[collection]
            
            total = col.estimated_document_count()
            
            # Get documents with pagination
            cursor = col.find().skip(skip).limit(limit).sort("Date", -1)
            documents = []
            
            for doc in cursor:
                doc['_id'] = str(doc['_id'])
                documents.append(doc)
            
            return {"documents": documents, "total": total}
        except Exception as e:
            print(f"Error getting documents: {e}")
            return {"documents": [], "total": 0}
    
    def query_documents(self, db_name: str, collection: str, query: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """Query documents with filter"""
        if not self._connected:
            return []
        
        try:
            if Database:
                client = self.db.conn
            else:
                client = self.client
            
            db = client[db_name]
            col = db[collection]
            
            cursor = col.find(query).limit(limit).sort("Date", -1)
            documents = []
            
            for doc in cursor:
                doc['_id'] = str(doc['_id'])
                documents.append(doc)
            
            return documents
        except Exception as e:
            print(f"Error querying documents: {e}")
            return []
    
    def get_today_news_count(self) -> int:
        """Get today's news count"""
        if not self._connected:
            return 0
        
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            total = 0
            
            # Query all news databases
            news_dbs = ["east_money_news", "jrj_news", "nbd_news", "net_ease_news"]
            
            for db_name in news_dbs:
                try:
                    if Database:
                        client = self.db.conn
                    else:
                        client = self.client
                    
                    db = client[db_name]
                    for col_name in db.list_collection_names():
                        count = db[col_name].count_documents({"Date": {"$regex": f"^{today}"}})
                        total += count
                except Exception:
                    continue
            
            return total
        except Exception as e:
            print(f"Error getting today's news count: {e}")
            return 0
    
    def get_sentiment_distribution(self) -> List[Dict[str, Any]]:
        """Get sentiment distribution"""
        if not self._connected:
            return []
        
        try:
            distribution = {"利好": 0, "利空": 0, "中性": 0}
            
            news_dbs = ["east_money_news", "jrj_news", "nbd_news", "net_ease_news"]
            
            for db_name in news_dbs:
                try:
                    if Database:
                        client = self.db.conn
                    else:
                        client = self.client
                    
                    db = client[db_name]
                    for col_name in db.list_collection_names():
                        pipeline = [
                            {"$group": {"_id": "$Label", "count": {"$sum": 1}}}
                        ]
                        results = list(db[col_name].aggregate(pipeline))
                        for r in results:
                            if r['_id'] in distribution:
                                distribution[r['_id']] += r['count']
                except Exception:
                    continue
            
            total = sum(distribution.values())
            if total == 0:
                return []
            
            return [
                {"label": k, "count": v, "percentage": round(v / total * 100, 2)}
                for k, v in distribution.items()
            ]
        except Exception as e:
            print(f"Error getting sentiment distribution: {e}")
            return []
    
    def get_hot_stocks(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get hot stocks by news count"""
        if not self._connected:
            return []
        
        try:
            if Database:
                client = self.db.conn
            else:
                client = self.client
            
            db = client["stock_specific_news"]
            stocks = []
            
            for col_name in db.list_collection_names():
                try:
                    good_count = db[col_name].count_documents({"Label": "利好"})
                    bad_count = db[col_name].count_documents({"Label": "利空"})
                    
                    if good_count > 0 or bad_count > 0:
                        stocks.append({
                            "name": col_name,
                            "code": col_name,
                            "good_count": good_count,
                            "bad_count": bad_count,
                            "total": good_count + bad_count
                        })
                except Exception:
                    continue
            
            # Sort by good_count desc
            stocks.sort(key=lambda x: x["good_count"], reverse=True)
            return stocks[:limit]
        except Exception as e:
            print(f"Error getting hot stocks: {e}")
            return []

# Singleton instance
db_service = DatabaseService()
