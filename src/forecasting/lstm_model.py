import tensorflow as tf
from tensorflow.keras import Sequential
from tensorflow.keras.layers import Input,LSTM,Dropout,Dense

def build_lstm(n_features,horizon=24,learning_rate=.001):
    m=Sequential([Input(shape=(None,n_features)),LSTM(128,return_sequences=True),Dropout(.2),LSTM(64),Dropout(.2),Dense(64,activation="relu"),Dense(horizon)])
    m.compile(optimizer=tf.keras.optimizers.Adam(learning_rate),loss="mse",metrics=["mae"]); return m
