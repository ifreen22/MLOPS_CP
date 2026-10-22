from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from xgboost import XGBClassifier

def get_all_models(random_state=42):
    models = {
        "Logistic Regression": LogisticRegression(random_state=random_state, max_iter=1000),
        "Decision Tree": DecisionTreeClassifier(random_state=random_state),
        "Random Forest": RandomForestClassifier(random_state=random_state),
        "XGBoost": XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=random_state),
        "SVM": SVC(probability=True, random_state=random_state),
        "MLP Classifier": MLPClassifier(random_state=random_state, max_iter=1000)
    }
    try:
        from lightgbm import LGBMClassifier
        models["LightGBM"] = LGBMClassifier(random_state=random_state, verbose=-1)
    except ImportError:
        print("LightGBM not installed, skipping.")
        
    try:
        from catboost import CatBoostClassifier
        models["CatBoost"] = CatBoostClassifier(random_state=random_state, verbose=0)
    except ImportError:
        print("CatBoost not installed, skipping.")
        
    return models
