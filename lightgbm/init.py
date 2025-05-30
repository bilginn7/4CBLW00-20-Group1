import lightgbm as lgb
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn import metrics
from sklearn.metrics import accuracy_score
import re
import warnings

warnings.filterwarnings("ignore")

x_test = pd.read_parquet("../data/X_test.parquet")
x_train = pd.read_parquet("../data/X_train.parquet")
y_test = pd.read_parquet("../data/y_test.parquet")
y_train = pd.read_parquet("../data/y_train.parquet")

print(x_test.info())

def clean_column_names(df):
    df.columns = [re.sub(r'[^\w]', '_', col) for col in df.columns]
    return df

x_train["LSOA code"] = x_train["LSOA code"].astype("category")
x_test["LSOA code"] = x_test["LSOA code"].astype("category")

x_train = clean_column_names(x_train)
x_test = clean_column_names(x_test)

# regex to catch any character other than letters, numbers, or underscore
bad_pattern = re.compile(r'[^\w]')

bad_cols = [col for col in x_train.columns if bad_pattern.search(col)]
print("Columns with problematic characters:", bad_cols)

clf = lgb.LGBMClassifier(categorical_feature=["LSOA_code"])
clf.fit(x_train, y_train.values.ravel())

y_pred=clf.predict(x_test)

accuracy=accuracy_score(y_pred, y_test)
print('LightGBM Model accuracy score: {0:0.4f}'.format(accuracy_score(y_test, y_pred)))

y_pred_train = clf.predict(x_train)
print('Training-set accuracy score: {0:0.4f}'. format(accuracy_score(y_train, y_pred_train)))

# print the scores on training and test set

print('Training set score: {:.4f}'.format(clf.score(x_train, y_train)))

print('Test set score: {:.4f}'.format(clf.score(x_test, y_test)))

# view confusion-matrix
# Print the Confusion Matrix and slice it into four pieces

from sklearn.metrics import confusion_matrix
cm = confusion_matrix(y_test, y_pred)
print('Confusion matrix\n\n', cm)
print('\nTrue Positives(TP) = ', cm[0,0])
print('\nTrue Negatives(TN) = ', cm[1,1])
print('\nFalse Positives(FP) = ', cm[0,1])
print('\nFalse Negatives(FN) = ', cm[1,0])

from sklearn.metrics import classification_report
print(classification_report(y_test, y_pred))