import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
import pandas as pd
from Activation import ReLu
from Activation import ReLuTest
from FullyConnected import FullyConnected
from Activation import Sigmoid
from Output import LogLoss
from Output import Generator
from tqdm import tqdm
import time
import data_utils as utils


def createStochasticBatch(sourceBatch, batchSize):
    np.random.shuffle(sourceBatch)
    newArr = sourceBatch[:batchSize]
    return newArr


def createInput(batchSize):
    input = np.random.randint(256, size=(batchSize, 784))
    return input


def combineRealandFake(arr1, arr2):
    arrOut = np.append(arr1, arr2, axis=0)
    return arrOut


def ReluGAN(showEachEpoch):
    # np.random.seed(0)
    batchSize = 100  # batch size for stochastic gradient descent
    numClasses = 1  # legacy from 615. Allows you to train multiple GANs for different classes
    numFeatures = 12288  # number of pixels (features) in the flattened picture
    originalShape = (64, 64, 3)  # shape of the picture
    maxEpochs = 10   # number of epochs to run

    print("Reading training data. Please wait...")
    trainArr = utils.restorePickleArr()  # Get training data from pickle object

    # create column vector for labelling real and fake data.
    # This will be used by the discriminator to calculate its loss
    print("\nSet up target arrays based on batch size...")
    d_trainArrTarget = np.ones((batchSize, 1), dtype=int)  # real data are labeled 1
    d_fakeArrTarget = np.zeros((batchSize, 1), dtype=int)  # fake (generated) data are labeled 0
    targetArr_d = combineRealandFake(d_trainArrTarget, d_fakeArrTarget)  # combine (doesn't need to be a method)

    print("\nTraining...")
    for i in range(numClasses):  # for creating multiple GANs for multiple classes
        print("Index " + str(i) + "...")
        learningRate_G = 0.0001  # rate at which we update the weights in the generator
        learningRate_D = 0.0001  # rate at which we update the weights in the discriminator

        # Define the model
        # Generator
        FC_G1 = FullyConnected(numFeatures, numFeatures*2, learningRate_G)  # layer where learning actually happens
        relu_G1 = ReLu()  # activation layer. ReLu is fast and non-linear which makes it popular
        FC_G2 = FullyConnected(numFeatures*2, numFeatures, learningRate_G)  # layer where learning actually happens
        relu_G2 = ReLu()  # activation layer. ReLu is fast and non-linear which makes it popular
        objective_G = Generator()  # Output/objective layer. It's mostly used for calculating loss and gradients

        # Discriminator
        FC_D1 = FullyConnected(numFeatures, numFeatures*2, learningRate_D)  # layer where learning actually happens
        relu_D1 = ReLu()
        FC_D2 = FullyConnected(numFeatures*2, 1, learningRate_D)  # layer where learning actually happens
        sig_D = Sigmoid()  # Activation layer. Forces values between 0 and 1
        LL_D = LogLoss(targetArr_d)  # Output.objective layer. It's mostly used for calculating loss and gradients

        # Time to start training
        # parameters
        epoch = 1  # training iteration counter
        jChange = 100  # metric for stopping training if our loss doesn't change much between epochs

        batchArr = trainArr  # arrList[i] # if we had multiple classes you would load the arrays into this array
        mu = np.average(batchArr)  # get average for the entire data set
        sigma = np.std(batchArr)  # get the SD for the entire data set

        # while jChange > 10 ** -6 and epoch <= maxEpochs: # replaced with a loop with a progress bar
        for i in tqdm(range(maxEpochs)):  # print a progress bar, estimated time, and rate
            # print(i)
            # Fake input
            # Generate random data that has the same mean and SD as the training data
            input_f = np.random.normal(mu, sigma, size=(batchSize, numFeatures))
            # Real input
            input_r = createStochasticBatch(batchArr, batchSize)

            # Forward Prop
            X_f = FC_G1.forwardPropagate(input_f)
            X_f = relu_G1.forwardPropagate(X_f)
            X_f = FC_G2.forwardPropagate(X_f)
            X_f = relu_G2.forwardPropagate(X_f)  # Generated fake data

            input_d = combineRealandFake(input_r, X_f)

            X_d = FC_D1.forwardPropagate(input_d)
            X_d = relu_D1.forwardPropagate(X_d)
            X_d = FC_D2.forwardPropagate(X_d)
            X_d = sig_D.forwardPropagate(X_d)  # prediction by the discriminator (real=1 or fake=0)
            J_d = LL_D.eval(X_d)  # print this to see the loss for the discriminator

            # back prop discriminator
            grad = LL_D.gradient(X_d)  # calculate the gradient of discriminator
            grad = sig_D.backwardPropagate(grad)  # account for the activation layer changes
            grad = FC_D2.backwardPropagate(grad, epoch)
            grad = relu_D1.backwardPropagate(grad)
            FC_D1.backwardPropagate(grad, epoch)  # update weights and biases for discriminator

            # forward prop again b/c the generator should learn based on the updated discriminator, not the old one
            X_d = FC_D1.forwardPropagate(X_f)  # This time only forward prop the fake data from earlier
            X_d = relu_D1.forwardPropagate(X_d)
            X_d = FC_D2.forwardPropagate(X_d)
            X_d = sig_D.forwardPropagate(X_d)
            J_g = objective_G.eval(X_d)  # print this to see the loss for the generator

            # back again
            grad = objective_G.gradient(X_d)  # calculate the gradient of discriminator
            grad = sig_D.backwardPropagate(grad)  # account for the activation layer changes
            grad = FC_D2.backwardPropagateNoUpdate(grad)
            grad = relu_D1.backwardPropagate(grad)
            grad = FC_D1.backwardPropagateNoUpdate(grad)  # account for the FC layer in discriminator but dont update it
            grad = relu_G2.backwardPropagate(grad)  # account for the activation layer changes
            grad = FC_G2.backwardPropagate(grad, epoch)
            grad = relu_G1.backwardPropagate(grad)  # account for the activation layer changes
            FC_G1.backwardPropagate(grad, epoch)  # update weights and biases in fully connected layer for generator

            epoch += 1

            if showEachEpoch:
                best_index = np.argmax(X_d, axis=0)  # find index for the best fake image
                best = X_f[best_index]  # get the data for that image
                best = best.reshape(originalShape)  # reshape it to the original size
                utils.arrayToImage(best)  # show the image (currently also saves the image as Output.png)
                # utils.createImage(best, "d" + str(i) + "e" + str(epoch))  # legacy from 615
        if not showEachEpoch:
            print(X_d)
            best_index = np.argmax(X_d, axis=0)  # find index for the best fake image
            best = X_f[best_index]  # get the data for that image
            best = best.reshape(originalShape)  # reshape it to the original size
            utils.arrayToImage(best)  # show the image (currently also saves the image as Output.png)
            # utils.createImage(best, "d" + str(i) + "e" + str(epoch)) # legacy from 615


ReluGAN(True)
