from __future__ import division
from __future__ import print_function
# Basic python and data processing imports
import numpy as np

np.set_printoptions(suppress=True)  # Suppress scientific notation when printing small
# import h5py

import load_data_pairs as ld  # my scripts for loading data
import build_incept_model as bm  # Keras specification of SPEID model

# import matplotlib.pyplot as plt
from datetime import datetime
import util

# Keras imports
from keras.optimizers import RMSprop, Adam
from keras.callbacks import ModelCheckpoint, EarlyStopping, Callback
from keras.layers import Input, Convolution1D, MaxPooling1D, Merge, Dropout, Flatten, Dense, BatchNormalization, LSTM, \
    Activation, Bidirectional
from keras.optimizers import RMSprop, Adam
from keras.callbacks import ModelCheckpoint, EarlyStopping, Callback
from keras.models import Sequential
from keras.regularizers import l1, l2

# cell_lines = ['GM12878', 'HeLa-S3', 'HUVEC', 'IMR90', 'K562', 'NHEK']
cell_lines = ['K562', 'IMR90']
cell_lines_tests = ['GM12878', 'HeLa-S3', 'IMR90', 'K562']
# Model training parameters
num_epochs = 32
batch_size = 100
kernel_size = 96
training_frac = 0.9  # fraction of data to use for training

t = datetime.now().strftime('%Y-%m-%d-%H:%M:%S')
opt = Adam(lr=1e-5)  # opt = RMSprop(lr = 1e-6)

data_path = '/home/panwei/zhuan143/all_cell_lines/'
out_path = data_path
for cell_line in cell_lines:
    print('Loading ' + cell_line + ' data from ' + data_path)
    X_enhancers = None
    X_promoters = None
    labels = None
    X_enhancers = np.load(out_path + cell_line + '_enhancers.npy')
    X_promoters = np.load(out_path + cell_line + '_promoters.npy')
    labels = np.load(out_path + cell_line + '_labels.npy')
    training_idx = np.random.randint(0, int(X_enhancers.shape[0]), size=27000)
    valid_idx = np.random.randint(0, int(X_enhancers.shape[0]), size=3000)
    X_enhancers_tr = X_enhancers[training_idx, :, :]
    X_promoters_tr = X_promoters[training_idx, :, :]
    labels_tr = labels[training_idx]
    X_enhancers_ts = X_enhancers[valid_idx, :, :]
    X_promoters_ts = X_promoters[valid_idx, :, :]
    labels_ts = labels[valid_idx]
    input_enhancer = Input((3000, 4))
    input_promoter = Input((2000, 4))
    #model = bm.build_inception_base(input_enhancer, input_promoter, seq_length_en=3000, seq_length_pro=2000)
    #model = bm.build_inception_feature(input_enhancer, input_promoter, seq_length_en=3000, seq_length_pro=2000)
    model = bm.build_shared_projection(input_enhancer, input_promoter, seq_length_en=3000, seq_length_pro=2000)
    model.compile(loss='binary_crossentropy',
                  optimizer=opt,
                  metrics=["accuracy"])

    model.summary()


    # Define custom callback that prints/plots performance at end of each epoch
    class ConfusionMatrix(Callback):
        def on_train_begin(self, logs={}):
            self.epoch = 0
            self.precisions = []
            self.recalls = []
            self.f1_scores = []
            self.losses = []
            self.training_losses = []
            self.training_accs = []
            self.accs = []
            # plt.ion()

        def on_epoch_end(self, batch, logs={}):
            self.training_losses.append(logs.get('loss'))
            self.training_accs.append(logs.get('acc'))
            self.epoch += 1
            val_predict = model.predict_classes([X_enhancers, X_promoters], batch_size=batch_size, verbose=0)
            # util.print_live(self, labels, val_predict, logs)
            '''if self.epoch > 1: # need at least two time points to plot
                util.plot_live(self)'''


    # print '\nlabels.mean(): ' + str(labels.mean())
    print('Data sizes: ')
    print('[X_enhancers, X_promoters]: [' + str(np.shape(X_enhancers)) + ', ' + str(np.shape(X_promoters)) + ']')
    print('labels: ' + str(np.shape(labels)))

    # Instantiate callbacks
    confusionMatrix = ConfusionMatrix()
    # checkpoint_path = "/home/sss1/Desktop/projects/DeepInteractions/weights/test-delete-this-" + cell_line + "-basic-" + t + ".hdf5"
    # checkpointer = ModelCheckpoint(filepath=checkpoint_path, verbose = 1)
    tr_sample = X_enhancers_tr.shape[0]
    X_enhancers_Ftr = np.reshape(X_enhancers_tr, [tr_sample, 3000*4])
    X_promoters_Ftr = np.reshape(X_promoters_tr, [tr_sample, 2000*4])
    ts_sample = X_enhancers_ts.shape[0]
    X_enhancers_Fts = np.reshape(X_enhancers_ts, [tr_sample, 3000 * 4])
    X_promoters_Fts = np.reshape(X_promoters_ts, [tr_sample, 2000 * 4])
    # combine the label with regression target
    for i in range(tr_sample):
        if labels_tr[i] ==1:
            X_enhancers_Ftr[i, :] = X_enhancers_Ftr[i, :]*1
            X_promoters_Ftr[i, :] = X_promoters_Ftr[i, :]*1
        else:
            X_enhancers_Ftr[i, :] = X_enhancers_Ftr[i, :]*0
            X_promoters_Ftr[i, :] = X_promoters_Ftr[i, :]*0

    for i in range(ts_sample):
        if labels_ts[i] ==1:
            X_enhancers_Fts[i, :] = X_enhancers_Fts[i, :]*1
            X_promoters_Fts[i, :] = X_promoters_Fts[i, :]*1
        else:
            X_enhancers_Fts[i, :] = X_enhancers_Fts[i, :]*0
            X_promoters_Fts[i, :] = X_promoters_Fts[i, :]*0

    print('Running fully trainable model for exactly ' + str(num_epochs) + ' epochs...')
    model.fit([X_enhancers_tr, X_promoters_tr],
              [labels_tr, X_promoters_Ftr, X_enhancers_Ftr],
              validation_data=([X_enhancers_ts, X_promoters_ts], [labels_ts, X_promoters_Fts, X_enhancers_Fts]),
              batch_size=batch_size,
              nb_epoch=num_epochs,
              shuffle=True
             # callbacks=[confusionMatrix]  # checkpointer]
              )

    print('Running predictions...')
    print('Running predictions...')
    for cell_line_test in cell_lines_tests:
        X_enhancers_test = np.load(out_path + cell_line_test + '_enhancers.npy')
        X_promoters_test = np.load(out_path + cell_line_test + '_promoters.npy')
        labels_test = np.load(out_path + cell_line_test + '_labels.npy')

        y_score, Promoter_Pre, Enhancer_Pre = model.predict([X_enhancers_test, X_promoters_test], batch_size=50, verbose=1)
        np.save(('MultiTask_y_predict_Batch' + str(batch_size) + '_Kernel' + str(kernel_size) + cell_line + '_test' + cell_line_test), y_score)
    # np.save(('y_label'+cell_line), )
