from xgboost import XGBClassifier

import xgboost as xgb

xgb.train()


param = {
    "max_depth": 5,
    "eta": 1,
    "num_class": 4,
    "tree_method": "gpu_hist",
}

model = XGBClassifier(param, objective="multi:softmax")
