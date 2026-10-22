import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import roc_curve, precision_recall_curve, confusion_matrix
from sklearn.calibration import calibration_curve
try:
    import shap
except ImportError:
    shap = None

VIS_DIR = os.path.join(os.path.dirname(__file__), "visualizations")
os.makedirs(VIS_DIR, exist_ok=True)

def plot_roc_curve(y_true, y_prob, model_name):
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, label=f'{model_name} ROC')
    plt.plot([0, 1], [0, 1], 'k--')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('ROC Curve')
    plt.legend()
    plt.savefig(os.path.join(VIS_DIR, "roc_curve.png"))
    plt.close()

def plot_pr_curve(y_true, y_prob, model_name):
    precision, recall, _ = precision_recall_curve(y_true, y_prob)
    plt.figure(figsize=(8, 6))
    plt.plot(recall, precision, label=f'{model_name} PR')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title('Precision-Recall Curve')
    plt.legend()
    plt.savefig(os.path.join(VIS_DIR, "pr_curve.png"))
    plt.close()

def plot_confusion_matrix(y_true, y_pred, model_name):
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.title(f'Confusion Matrix ({model_name})')
    plt.savefig(os.path.join(VIS_DIR, "confusion_matrix.png"))
    plt.close()

def plot_calibration_curve(y_true, y_prob, model_name):
    prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=10)
    plt.figure(figsize=(8, 6))
    plt.plot(prob_pred, prob_true, marker='o', label=model_name)
    plt.plot([0, 1], [0, 1], 'k--')
    plt.xlabel('Mean predicted probability')
    plt.ylabel('Fraction of positives')
    plt.title('Calibration Curve')
    plt.legend()
    plt.savefig(os.path.join(VIS_DIR, "calibration_curve.png"))
    plt.close()

def plot_prediction_distribution(y_prob, model_name):
    plt.figure(figsize=(8, 6))
    sns.histplot(y_prob, bins=50, kde=True, color='purple')
    plt.xlabel('Predicted Risk Probability')
    plt.ylabel('Frequency')
    plt.title(f'Prediction Distribution ({model_name})')
    plt.savefig(os.path.join(VIS_DIR, "prediction_distribution.png"))
    plt.close()

def plot_feature_importance(model, feature_names):
    if hasattr(model, 'feature_importances_'):
        importances = model.feature_importances_
        idx = np.argsort(importances)[::-1]
        
        plt.figure(figsize=(10, 8))
        sns.barplot(x=importances[idx], y=np.array(feature_names)[idx], palette='viridis')
        plt.title("Feature Importance")
        plt.xlabel("Relative Importance")
        plt.tight_layout()
        plt.savefig(os.path.join(VIS_DIR, "feature_importance.png"))
        plt.close()

def plot_shap_summary(model, X_train, feature_names):
    if shap is None:
        print("SHAP not installed, skipping.")
        return
    try:
        explainer = shap.TreeExplainer(model)
        # Calculate SHAP values for a subset to save time
        X_sample = X_train[:500]
        shap_values = explainer.shap_values(X_sample)
        
        # Binary classification SHAP shapes vary
        if isinstance(shap_values, list):
            shap_values = shap_values[1]
            
        plt.figure(figsize=(10, 8))
        shap.summary_plot(shap_values, X_sample, feature_names=feature_names, show=False)
        plt.tight_layout()
        plt.savefig(os.path.join(VIS_DIR, "shap_summary.png"))
        plt.close()
    except ImportError:
        print("SHAP not installed, skipping.")
    except Exception as e:
        print(f"SHAP explainer failed: {e}")

def plot_learning_curve(train_sizes, train_scores, test_scores):
    train_mean = np.mean(train_scores, axis=1)
    train_std = np.std(train_scores, axis=1)
    test_mean = np.mean(test_scores, axis=1)
    test_std = np.std(test_scores, axis=1)
    
    plt.figure(figsize=(8, 6))
    plt.plot(train_sizes, train_mean, 'o-', color="r", label="Training score")
    plt.plot(train_sizes, test_mean, 'o-', color="g", label="Cross-validation score")
    plt.fill_between(train_sizes, train_mean - train_std, train_mean + train_std, alpha=0.1, color="r")
    plt.fill_between(train_sizes, test_mean - test_std, test_mean + test_std, alpha=0.1, color="g")
    
    plt.xlabel("Training examples")
    plt.ylabel("Score")
    plt.title("Learning Curve")
    plt.legend(loc="best")
    plt.savefig(os.path.join(VIS_DIR, "learning_curve.png"))
    plt.close()
