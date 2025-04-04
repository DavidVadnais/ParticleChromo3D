from Swarm import Swarm
import Helper

import sys
import copy
import time
import argparse
import os

import numpy as np
from scipy import stats

from multiprocessing import Pool
from multiprocessing import cpu_count
from itertools import repeat

from Helper import Write_Log

def lossFunction(tar,b,lossFunc = 0):
    if (lossFunc == 1):
        newCost = np.sum( (b-tar)**2, axis=1 )/len(b)#MSE
    elif(lossFunc == 2):
        newCost = np.sqrt(np.sum( (b-tar)**2, axis=1 ))#RMSE
    elif(lossFunc == 3):
        #Heuber
        delta = 1.0
        y = tar
        yHat = b
        newCost = np.sum(np.where(np.abs(y-yHat) < delta,.5*(y-yHat)**2 , delta*(np.abs(y-yHat)-0.5*delta)))
    else :
        newCost = np.sum( (b-tar)**2)#SSE
    return newCost

# Prints statistics of the current swarm
def Print_Stats(swarm, contact, pointCount, i, outFilePtr, convFact):
    pers = stats.pearsonr(swarm.gBest[2], contact[:,3])
    spear = stats.spearmanr(swarm.gBest[2], contact[:,3])
    spearIF = stats.spearmanr(swarm.gBest[2], contact[:,2])

    error = np.sqrt( (1/pointCount) * np.sum( (swarm.gBest[2]-contact[:,3])**2 ) )

    print('id: ' + str(swarm.id) + 
        ' itt: ' + str(i) + 
        ' Cost: ' + str(swarm.gBest[1]) + 
        ' Pearson: ' + str(pers[0]) + 
        ' Spearmen: ' + str(spear[0]) +
        ' IFSpear: ' + str(spearIF[0]) +
        ' error: ' + str(error))
    thisOutFilePtr = 'outputFolder/'+outFilePtr +str(convFact)
    

def Write_Stats(swarm, contact, outFilePtr):
    Helper.Write_Output(outFilePtr, swarm.gBest[0])

# Performs one operation and prints statistics of current swarm
def One_Move(ittCount, swarm, contact, pointCount, threshold,  outFilePtr, convFact):
    saveGBestCost = float('inf')
    totTime = 0


    for i in range(ittCount):
        if (i%1000 == 0) and (swarm.gBest is not None):
            #error = np.sqrt( (1/pointCount) * np.sum( (swarm.gBest[2]-contact[:,3])**2 ) )
            error = lossFunction(contact[:,3],swarm.gBest[2])#np.sum( (swarm.gBest[2]-contact[:,3])**2 )
            Print_Stats(swarm, contact, pointCount, i, outFilePtr, convFact)
            
                

            if (np.abs(saveGBestCost - error)) >= threshold:
                saveGBestCost = error
            else:
                return i, totTime

        operation(i, swarm)


    return i

# Performs a single PSO pass: Velocity calculation, update position, get new cost
def operation(i, swarm):
    swarm.Calc_Vel(ittCount,i)
    swarm.Update_Pos(i)
    swarm.Cost()

# Optimizes single swarm
def Optimize(inFilePtr, outFilePtr, convFact,constraint,points,zeroInd , lossFunctionChoice =0):
    dist = 1.0 / (constraint[:,2]**convFact)
    constraint = np.insert(constraint,3, dist ,axis=1)
    
    swarm = Swarm(constraint, len(points), randVal=randRange, swarmSize=swarmSize, zeroInd=zeroInd, lossFunc = lossFunctionChoice)

    ittFin = One_Move(ittCount, swarm, constraint, len(points), threshold,  outFilePtr, convFact)
    return (stats.pearsonr(swarm.gBest[2], constraint[:,3])[0], 
                    stats.spearmanr(swarm.gBest[2], constraint[:,3])[0], 
                    lossFunction(constraint[:,3],swarm.gBest[2]),
                    ittFin,
                     swarm.id, swarm)

# Runs in paralel if passed multiple rangeSpace
def Par_Choice(inFilePtr, outFilePtr, alpha,lossFunctionChoice =0 ):
    contact, points, zeroInd = Helper.Read_Data(inFilePtr, alpha)
    
    bestSwarm = None
    if 1==1:
        convStore = []
        alphas = np.array(range(int(alpha[0]), int(alpha[1]), int(alpha[2])))/100
        pool = Pool(processes=PROC_COUNT)
        swarms = pool.starmap(Optimize,  zip(repeat(inFilePtr), repeat(outFilePtr), 
                                             alphas, 
                                             repeat(contact),repeat(points),repeat(zeroInd),repeat(lossFunctionChoice)))

        pool.close()
        pool.join()

        #swarms = sorted(swarms, key=lambda x: x[1])
        
        iforapl = 0
        for swarm in swarms:
            print(str(swarm[-1]) + ' ' + str(swarm[1]))
            convStore.append(swarm)
            if (bestSwarm is None) or (swarm[1] > bestSwarm[1]):
                bestSwarm = swarm
                swarmForPDB = swarm[len(swarm)-1]
                bestAlpha = alphas[iforapl]
            iforapl += 1
    else:
        bestSwarm = Optimize( inFilePtr, outFilePtr, alpha)
    contact = np.insert(contact,3, 1.0 / (contact[:,2]**bestAlpha) ,axis=1)
    print(bestSwarm)
    Write_Stats(swarmForPDB, contact, outFilePtr)

    return bestSwarm

def Full_List( inputFilePtr, outFilePtr , alpha, lossFunctionChoice = 0):
    convStore = []
    
    convStore.append(Par_Choice( inputFilePtr, outFilePtr, alpha, lossFunctionChoice=lossFunctionChoice))
    print("pearson:" + str(convStore[0][0]) + " spearman:"+
          str(convStore[0][1]) + " rmse:" + str(convStore[0][2]))

    #Helper.Write_List(convStore, outFilePtr)
    return convStore

sys.setrecursionlimit(10000)
if cpu_count() <= 2:
    PROC_COUNT = cpu_count()
else :
    PROC_COUNT = cpu_count()-1#attempt to reduce thrashing.



rangeSpace = [] # Max scaling factor. Needs to be optimized for each specific dataset. Use two values [one, two] to multithread through a range of those two values at a interval of 5000


# Arguments for running program
# python3 ParticleChromo3D.py <input_data> <other_parameter>
parser = argparse.ArgumentParser("ParticleChromo3D")
parser.add_argument("infile", help="Matrix of contacts", type=str)
parser.add_argument("-ss","--swarmSize", help="Number of particles in system [Default 15]", type=int, default=15)
parser.add_argument("-itt","--ittCount", help="Maximum itterations before stop [Default 30000]", type=int, default=30000)
parser.add_argument("-t","--threshold", help="Error threshold before stoping [Default 0.000001]", type=float, default=0.000001)
parser.add_argument("-rr","--randRange", help="Range of x,y,z starting coords. Random value bewtween -randRange,randRange [Default 1]", type=float, default=1.0)
parser.add_argument("-o","--outfile", help="Filename of the output pdb model  [Default ./chr.pdb]", type=str, default="./chr.pdb")
parser.add_argument("-lf","--lossFunction", help="0 = SSE, 1 = MSE, 2 = RMSE, 3 = Huber - if Huber set desired cut parameter [Default 2]", type=int, default=2)



args = parser.parse_args()

if args.infile:
    inFilePtr = args.infile
if args.outfile:
    outFilePtr = args.outfile
else: 
    outFilePtr = "noIn"
if args.swarmSize:
    swarmSize = args.swarmSize
if args.ittCount:
    ittCount = args.ittCount
if args.threshold:
    threshold = args.threshold
if args.randRange:
    randRange = args.randRange

lossFunctionChoice = args.lossFunction
    
if len(rangeSpace) == 0:
    rangeSpace.append(20000)

if len(rangeSpace) > 2 and (rangeSpace[0] == rangeSpace[1]):
    rangeSpace.pop()   

print(inFilePtr)

fout = inFilePtr + ".stripped"
clean_lines = []
f= open(inFilePtr, "r")
lines = f.readlines()
for l in lines:
    res = str(" ".join(l.split()))
    clean_lines.append(res)
f.close()

with open(fout, "w") as f:
    f.writelines('\n'.join(clean_lines))
f.close()


theseAlphas = np.array([0.1, 2.0, 0.1])*100
theAlphas = np.array(range(int(theseAlphas[0]),int(theseAlphas[1]),int(theseAlphas[2])))/100

if outFilePtr == "noIn":
    outFilePtr =  os.path.basename(os.path.basename(inFilePtr))
    outFilePtr = os.path.splitext(outFilePtr)[0]
    print(outFilePtr)
outputOfSwarm = Full_List( inFilePtr+".stripped", outFilePtr, theseAlphas, lossFunctionChoice)[0]
print(outputOfSwarm)

bestSpearm = outputOfSwarm[1]
bestCost = outputOfSwarm[2]
bestAlpha = theAlphas[outputOfSwarm[4]]
bestPearsonRHO = outputOfSwarm[0]

    
print("Input file: ", inFilePtr)
print("Convert factor:: ",bestAlpha)
print("SSE at best spearman : ", bestCost)    
print("Best Spearman correlation Dist vs. Reconstructed Dist  : ", bestSpearm) 
print("Best Pearson correlation Dist vs. Reconstructed Dist: ", bestPearsonRHO) 
Write_Log(outFilePtr +".log", inFilePtr, bestAlpha, bestCost, bestSpearm, bestPearsonRHO)
