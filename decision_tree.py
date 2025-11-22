import numpy as np
import kagglehub
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_percentage_error
class DecisionTree:
    def __init__(self, min_count = 15, mode='Regression'):
        self.root = None
        self.min_count = min_count
        self.mode = mode

    def fit(self, features, target):
        self.root = Node(features, target)
        self.recursive_fit(self.root)
        return self.root

    def recursive_fit(self, current_node):
        # check stop conditions :o
        if current_node is None:
            return
        if current_node.features.shape[0] < self.min_count:
            return

        left_features, left_targets, right_features, right_targets, category, threshold, error = current_node.best_split()
        current_node.threshold = threshold
        current_node.category = category

        if category is None:
            return

        if left_features.shape[0] > 0:
            current_node.left = Node(left_features, left_targets)
        if right_features.shape[0] > 0:
            current_node.right = Node(right_features, right_targets)

        self.recursive_fit(current_node.left)
        self.recursive_fit(current_node.right)

    def predict(self, features):
        out = np.zeros(features.shape[0])
        for i in range(features.shape[0]):
            current_node = self.root
            while current_node is not None:
                out[i] = current_node.value
                if current_node.left is None and current_node.right is None:
                    break

                if features[i][current_node.category] < current_node.threshold:
                    current_node = current_node.left
                else:
                    current_node = current_node.right
        return out

class Node:
    def __init__(self, features, targets, mode='Regression'):
        self.mode = mode
        self.features = features
        self.targets = targets
        self.left = None
        self.right = None
        if mode == "Regression":
            self.value = np.mean(targets)
        else:
            values, counts = np.unique(targets, return_counts=True)
            self.value = values[counts.argmax()]

        # Initialize split criteria to None
        self.category = None
        self.threshold = None

    def split(self, split_category, threshold):
        ind = np.argsort( self.features[:,split_category] )
        sorted_features = self.features[ind]
        sorted_targets = self.targets[ind]

        threshold_index = np.searchsorted(sorted_features[:,split_category], threshold, side='left')
        left_features = sorted_features[:threshold_index,:]
        left_targets = sorted_targets[:threshold_index]
        right_features = sorted_features[threshold_index:,:]
        right_targets = sorted_targets[threshold_index:]

        return left_features, left_targets, right_features, right_targets

    def compute_gini(self, target):
        values, counts = np.unique(target, return_counts=True)
        G = 1
        for c in counts:
            pk = c/target.shape[0]
            G -= pk**2
        return G

    def compute_sum_squared_error(self, features, target):
        mean = np.mean(target)
        return np.sum((target - mean) ** 2)

    def compute_error(self, features, target):
        if self.mode == "Regression":
            return self.compute_sum_squared_error(features, target)
        else:
            return self.compute_gini(target)

    def best_split(self):
        min_error = float('inf')
        min_category = None
        min_threshold = None
        min_left_features = None
        min_left_targets = None
        min_right_features = None
        min_right_targets = None

        for category in range(self.features.shape[1]):
            uniques = np.unique(self.features[:,category])
            for i in range(len(uniques)-1):

                threshold = (uniques[i] + uniques[i+1])/2
                left_features, left_targets, right_features, right_targets = self.split(category, threshold)

                error = self.compute_error(left_features, left_targets) + self.compute_error(right_features, right_targets)

                if error < min_error:

                    min_error = error
                    min_threshold = threshold
                    min_category = category
                    min_left_features = left_features
                    min_left_targets = left_targets
                    min_right_features = right_features
                    min_right_targets = right_targets

        return min_left_features, min_left_targets, min_right_features, min_right_targets, min_category, min_threshold, min_error



path = kagglehub.dataset_download("yasserh/housing-prices-dataset")

df = pd.read_csv(path + '/Housing.csv')

bool_columns= ['mainroad', 'guestroom', 'basement', 'hotwaterheating', 'airconditioning','prefarea']
df[bool_columns] = df[bool_columns].replace({"yes": 1, "no": 0}).astype(int)
df['furnishingstatus'] = df['furnishingstatus'].replace({"furnished": 1, "semi-furnished": 0, "unfurnished": 0}).astype(int)


pd_targets = df['price']
pd_features = df.drop('price',axis=1)

np_target = np.array(pd_targets)
np_features = np.array(pd_features)


X_train, X_test, y_train, y_test = train_test_split(
    np_features, np_target, test_size=0.33, random_state=42)

d = DecisionTree()
d.fit(X_train, y_train)

y_pred = d.predict(X_test)

print(mean_absolute_percentage_error(y_test, y_pred))
