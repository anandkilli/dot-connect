import CHIP_IO.GPIO as GPIO
import time
from bitstring import BitArray as bitarray
import threading
import subprocess as sp
from enum import Enum
import copy
import pyjoy

#define pins to be used for driving shift registers
dataPin = "CSID3"
clockPin = "CSID5"
latchPin = "CSID7"

#Set pins in Output mode
GPIO.setup(dataPin, GPIO.OUT)
GPIO.setup(clockPin, GPIO.OUT)
GPIO.setup(latchPin, GPIO.OUT)


# 24x8 Bit matrix representing 8 rows and 8 columns of RGB leds. 3 bits for each led
# 0 means the led is ON and 1 means OFF

bitMatrix = [bitarray(bin='111111111111011111111111'),
	     bitarray(bin='111111111111100111101001'),
	     bitarray(bin='111111111111101001111100'),
	     bitarray(bin='111111111010001111111111'),
	     bitarray(bin='111111111111010111111111'),
	     bitarray(bin='111111111111110111111111'),
	     bitarray(bin='111111111111111111111111'),
	     bitarray(bin='111011111111111111111111')]

emptyMatrix = [bitarray(bin='111111111111111111111111'),
	     bitarray(bin='111111111111111111111111'),
	     bitarray(bin='111111111111111111111111'),
	     bitarray(bin='111111111111111111111111'),
	     bitarray(bin='111111111111111111111111'),
	     bitarray(bin='111111111111111111111111'),
	     bitarray(bin='111111111111111111111111'),
	     bitarray(bin='111111111111111111111111')]

tickMarkPos = [[5,1],[6,2],[7,3],[6,4],[5,5],[4,6],[3,7],[2,8]]

class Direction(Enum):
	LEFT = 1
	RIGHT = 2
	UP = 3
	DOWN = 4
	
# Initialize empty dot positions array
dotOrigPositions = []
dotCurPositions = []
levelStatus = bitarray(bin='0')
#Current game level
curLevel = 0
curIndex = 0
tflag = True

modifiedMatrix = []
def rearrangeBits():
	modifiedMatrix.clear()
	for r in range(len(bitMatrix)):
		#print("Rearranging row:",r," BitRow:",bitMatrix[r])
		tempRow = bitarray(24)
		tempRow[8] = bitMatrix[r][0] #LED1 Red
		tempRow[23] = bitMatrix[r][1] #LED1 Green
		tempRow[0] = bitMatrix[r][2] #LED1 Blue
		tempRow[9] = bitMatrix[r][3] #LED2 Red
		tempRow[22] = bitMatrix[r][4] #LED2 Green
		tempRow[1] = bitMatrix[r][5] #LED2 Blue
		tempRow[10] = bitMatrix[r][6] #LED3 Red
		tempRow[21] = bitMatrix[r][7] #LED3 Green
		tempRow[2] = bitMatrix[r][8] #LED3 Blue
		tempRow[11] = bitMatrix[r][9] #LED4 Red
		tempRow[20] = bitMatrix[r][10] #LED4 Green
		tempRow[3] = bitMatrix[r][11] #LED4 Blue
		tempRow[12] = bitMatrix[r][12] #LED5 Red
		tempRow[19] = bitMatrix[r][13] #LED5 Green
		tempRow[4] = bitMatrix[r][14] #LED5 Blue
		tempRow[13] = bitMatrix[r][15] #LED6 Red
		tempRow[18] = bitMatrix[r][16] #LED6 Green
		tempRow[5] = bitMatrix[r][17] #LED6 Blue
		tempRow[14] = bitMatrix[r][18] #LED7 Red
		tempRow[17] = bitMatrix[r][19] #LED7 Green
		tempRow[6] = bitMatrix[r][20] #LED7 Blue
		tempRow[15] = bitMatrix[r][21] #LED8 Red
		tempRow[16] = bitMatrix[r][22] #LED8 Green
		tempRow[7] = bitMatrix[r][23] #LED8 Blue
		modifiedMatrix.append(copy.deepcopy(tempRow))

def shiftOut(data,dataPin,clockPin):
	#Set clock pin to LOW to prepare writing data to buffer
	GPIO.output(clockPin, GPIO.LOW)
	for i in range(len(data)): 
		#Send bit to data pin. Set it to HIGH if 1 is found, LOW otherwise
		if(data[len(data)-i-1]): 
			GPIO.output(dataPin, GPIO.HIGH)
		else: 
			GPIO.output(dataPin, GPIO.LOW)

		#Set and reset the clock to high to accept the data
		GPIO.output(clockPin, GPIO.HIGH)
		GPIO.output(clockPin, GPIO.LOW)

def printMatrixAnime():
	while tflag:
		try:
			for r in range(len(modifiedMatrix)): 
				rowData = bitarray(bin='00000000')
				rowData[r] = 1
				shiftOut(rowData, dataPin, clockPin)
				shiftOut(modifiedMatrix[r], dataPin, clockPin)
				#Set latch pin to HIGH
				GPIO.output(latchPin, GPIO.HIGH)
				GPIO.output(latchPin, GPIO.LOW)
				time.sleep(0.0001)
		except:
			pass

def printMatrix():
	while not all(levelStatus):
		try:
			for r in range(len(modifiedMatrix)): 
				rowData = bitarray(bin='00000000')
				rowData[r] = 1
				shiftOut(rowData, dataPin, clockPin)
				shiftOut(modifiedMatrix[r], dataPin, clockPin)
				#Set latch pin to HIGH
				GPIO.output(latchPin, GPIO.HIGH)
				GPIO.output(latchPin, GPIO.LOW)
				time.sleep(0.0001)
		except:
			pass
		

def blinkCurDot():
	while not all(levelStatus):
		try:
			curDot = dotCurPositions[curIndex]
			ledNum = int((curDot[1]+3)/3)
			ledPos = getLedMappings(ledNum)
			bit1,modifiedMatrix[curDot[0]][ledPos[0]] = copy.deepcopy(modifiedMatrix[curDot[0]][ledPos[0]]),1 #LED6 Red
			bit2,modifiedMatrix[curDot[0]][ledPos[1]] = copy.deepcopy(modifiedMatrix[curDot[0]][ledPos[1]]),1 #LED6 Green
			bit3,modifiedMatrix[curDot[0]][ledPos[2]] = copy.deepcopy(modifiedMatrix[curDot[0]][ledPos[2]]),1 #LED6 Blue
			time.sleep(0.25)
			modifiedMatrix[curDot[0]][ledPos[0]] = copy.deepcopy(bit1)
			modifiedMatrix[curDot[0]][ledPos[1]] = copy.deepcopy(bit2)
			modifiedMatrix[curDot[0]][ledPos[2]] = copy.deepcopy(bit3)
			time.sleep(0.25)
		except:
			pass

def loadNextLevel():
	#Read level from file and load in bitMatrix
	global curLevel
	global dotCurPositions
	global dotOrigPositions
	global levelStatus
	global tflag
	curLevel += 1
	#Showing level number on dot matrix display
	dig = str("%02d" % curLevel)
	digitData = open("dotconnect-digits.txt", "r")
	digitData.seek((int(dig[0]))*123+9)
	for k in range(8):
		bitMatrix[k] = bitarray(bin=digitData.readline())
	digitData.seek((int(dig[1]))*123+9)
	secondDigit = []
	for k in range(8):
		secondDigit.append(bitarray(bin=digitData.readline()))
	for i in range(8):
		bitMatrix[i].append(secondDigit[i])
	rearrangeBits()
	tflag = True
	thrd = threading.Thread(target=printMatrixAnime)
	thrd.start()
	time.sleep(3)
	tflag = False
	levelData = open("dotconnect-levels.txt", "r") 
	levelData.seek((curLevel-1)*210+9)
	for i in range(8):
		bitMatrix[i] = bitarray(bin=levelData.readline())

	# Scan the matrix and identify the dots, i.e. any set of 3 bits containing at least one 0
	dotOrigPositions.clear()
	for r in range(len(bitMatrix)): 
			for c in range(0,len(bitMatrix[r]),3):
				if(not all(bitMatrix[r][c:c+3])):
					dotOrigPositions.append([r,c])
	
	# Copy original positions into current positions to keep track of last dot in the line
	dotCurPositions.clear()
	dotCurPositions = copy.deepcopy(dotOrigPositions)
	
	#  Initialize boolean array for tracking how many lines are connected
	levelStatus.clear()
	levelStatus = bitarray(bin='0') * len(dotOrigPositions)
	curIndex = 0
	t = threading.Thread(target=printMatrix)
	bt = threading.Thread(target=blinkCurDot)
	t.start()
	bt.start()

loadNextLevel()

# Module to check the boundaries 
def boundaryCheck(direction, position):
	posRow = position[0]
	posCol = int(position[1]/3)
	
	if (direction == Direction.LEFT and posCol == 0): return False
	elif (direction == Direction.RIGHT and posCol == 7): return False
	elif (direction == Direction.UP and posRow == 0): return False
	elif (direction == Direction.DOWN and posRow == 7): return False
	else: return True

def clearLine(index):
	# Clears all the dots in the line for the given index (Clears same colored dots
	try:
		curColor = bitMatrix[dotCurPositions[index][0]][dotCurPositions[index][1]:dotCurPositions[index][1]+3]
		print("curColor:", curColor, "Index: ", index)
		for r in range(len(bitMatrix)): 
			for c in range(0,len(bitMatrix[r]),3):
				temp = bitMatrix[r][c:c+3]
				if(not all(temp)): # Non blank dot test
					if(temp == curColor and [r,c] not in dotOrigPositions): 
						# Clear the dot if color matches and it is not one of the source and destination dots
						bitMatrix[r][c:c+3] = bitarray(bin='111')
		# Clear the bits in levelStatus
		levelStatus[index] = 0
		levelStatus[getTheOtherEnd(index)] = 0

	except: print("There was an exception while clearing the dots")
	else: dotCurPositions[index] = copy.deepcopy(dotOrigPositions[index])

def getTheOtherEnd(index):
	# Return the index of matching color dot for the given "index"
	temp = dotOrigPositions[index]
	for i in range(len(dotOrigPositions)):
		if i == index: continue
		else:
			colorToMatch = dotOrigPositions[i]
			if bitMatrix[temp[0]][temp[1]:temp[1]+3] == bitMatrix[colorToMatch[0]][colorToMatch[1]:colorToMatch[1]+3]:
				print("Index: ", index, "colorToMatch ", i)
				return i

def getLedMappings(ledNum):
	if ledNum == 1:
		return [8,23,0]
	if ledNum == 2:
		return [9,22,1]
	if ledNum == 3:
		return [10,21,2]
	if ledNum == 4:
		return [11,20,3]
	if ledNum == 5:
		return [12,19,4]
	if ledNum == 6:
		return [13,18,5]
	if ledNum == 7:
		return [14,17,6]
	if ledNum == 8:
		return [15,16,7]


		
rearrangeBits()

def handleLevelComplete():
	global bitMatrix
	global emptyMatrix
	global tickMarkPos
	global tflag
	print("Showing level complete animation")
	rowData = bitarray(bin='00000000')
	for i in range(5):
		for i in range(15):
			try:
				for r in range(len(modifiedMatrix)): 
					rowData = bitarray(bin='00000000')
					rowData[r] = 1
					shiftOut(rowData, dataPin, clockPin)
					shiftOut(modifiedMatrix[r], dataPin, clockPin)
					#Set latch pin to HIGH
					GPIO.output(latchPin, GPIO.HIGH)
					GPIO.output(latchPin, GPIO.LOW)
					time.sleep(0.0001)
			except:
				pass
		for k in range(8):
			try:
				shiftOut(rowData, dataPin, clockPin)
				shiftOut(bitarray(bin='1') * 24, dataPin, clockPin)
				#Set latch pin to HIGH
				GPIO.output(latchPin, GPIO.HIGH)
				GPIO.output(latchPin, GPIO.LOW)
			except:
				pass
		time.sleep(0.25)
	bitMatrix = copy.deepcopy(emptyMatrix)
	rearrangeBits()
	tflag = True
	thrd = threading.Thread(target=printMatrixAnime)
	thrd.start()
	for i in range(len(tickMarkPos)):
		r = tickMarkPos[i][0]-1
		c = (tickMarkPos[i][1]-1)*3
		#print(r," ",c)
		bitMatrix[r][c:c+3] = bitarray(bin='101')
		rearrangeBits()
		time.sleep(0.10);
	time.sleep(1)
	tflag = False
		
#Define thread that accepts keystrokes and manipulate matrix
def keyscan():
	global curIndex
	global bitMatrix
	global dotCurPositions
	global dotOrigPositions
	while True:
		#key = input("Press a key: ")
		key = pyjoy.getButton()
		if (key == 'base3'): break
		if (key == 'x: -1'):
			# Left arrow pressed
			# Check if an operation needs to be performed or not
			result = boundaryCheck(Direction.LEFT, dotCurPositions[curIndex])
			print("Result: ", result)
			# If operation is allowed, copy the 3 bits in current position to the bits on left 
			if result:
				posRow = dotCurPositions[curIndex][0]
				posCol = int(dotCurPositions[curIndex][1]/3)*3
				print("Next dot: ", bitMatrix[posRow][posCol-3:posCol])
				if all(bitMatrix[posRow][posCol-3:posCol]) :
					# All the bits are '1' so the next dot is blank
					# Before extending the line check if there is already a line with the same color. This check is needed only once when the line starts
					if (dotCurPositions[curIndex] == dotOrigPositions[curIndex]):
						clearLine(getTheOtherEnd(curIndex))
					bitMatrix[posRow][posCol-3:posCol] = bitMatrix[posRow][posCol:posCol+3]
					dotCurPositions[curIndex][1] -= 3
				else:
					# Next dot is not blank. See if it is the same color dot in which case the line will complete 
					print("Non blank dot found")
					if(bitMatrix[posRow][posCol-3:posCol] == bitMatrix[posRow][posCol:posCol+3]):
						print("Next dot is same color")
						# Dot is same color but check if it is one of the destination dots.
						if([dotCurPositions[curIndex][0],dotCurPositions[curIndex][1]-3] in dotCurPositions): 
							print("Line connected")
							dotCurPositions[curIndex] = copy.deepcopy(dotOrigPositions[curIndex])
							levelStatus[curIndex] = 1
							levelStatus[getTheOtherEnd(curIndex)] = 1
							if(all(levelStatus)): 
								print("It's a Game...")
								handleLevelComplete()
								loadNextLevel()
		elif (key == 'x: 1'):
			# Right arrow pressed
			# Check if an operation needs to be performed or not
			result = boundaryCheck(Direction.RIGHT, dotCurPositions[curIndex])
			print("Result: ", result)
			# If operation is allowed, copy the 3 bits in current position to the bits on left 
			if result:
				posRow = dotCurPositions[curIndex][0]
				posCol = int(dotCurPositions[curIndex][1]/3)*3
				print("Next dot", bitMatrix[posRow][posCol+3:posCol+6])
				if all(bitMatrix[posRow][posCol+3:posCol+6]) : 
					# All the bits are '1' so the next dot is blank
					# Before extending the line check if there is already a line with the same color. This check is needed only once when the line starts
					if (dotCurPositions[curIndex] == dotOrigPositions[curIndex]):
						clearLine(getTheOtherEnd(curIndex))
					bitMatrix[posRow][posCol+3:posCol+6]=bitMatrix[posRow][posCol:posCol+3]
					dotCurPositions[curIndex][1] += 3
				else:
					# Next dot is not blank. See if it is the same color dot in which case the line will complete 
					print("Non blank dot found")
					if(bitMatrix[posRow][posCol+3:posCol+6] == bitMatrix[posRow][posCol:posCol+3]):
						print("Next dot is same color")
						# Dot is same color but check if it is one of the destination dots.
						if([dotCurPositions[curIndex][0],dotCurPositions[curIndex][1]+3] in dotCurPositions): 
							print("Line connected")
							dotCurPositions[curIndex] = copy.deepcopy(dotOrigPositions[curIndex])
							levelStatus[curIndex] = 1
							levelStatus[getTheOtherEnd(curIndex)] = 1
							if(all(levelStatus)): 
								print("It's a Game...")
								handleLevelComplete()
								loadNextLevel()
		elif (key == 'y: -1'):
			# Up arrow pressed
			# Check if an operation needs to be performed or not
			result = boundaryCheck(Direction.UP, dotCurPositions[curIndex])
			print("Result: ", result)
			# If operation is allowed, copy the 3 bits in current position to the bits above 
			if result:
				posRow = dotCurPositions[curIndex][0]
				posCol = int(dotCurPositions[curIndex][1]/3)*3
				print("Next dot: ", bitMatrix[posRow-1][posCol:posCol+3])
				if all(bitMatrix[posRow-1][posCol:posCol+3]):
					# All the bits are '1' so the next dot is blank
					# Before extending the line check if there is already a line with the same color. This check is needed only once when the line starts
					if (dotCurPositions[curIndex] == dotOrigPositions[curIndex]):
						clearLine(getTheOtherEnd(curIndex))
					bitMatrix[posRow-1][posCol:posCol+3] = bitMatrix[posRow][posCol:posCol+3]
					dotCurPositions[curIndex][0] -= 1
				else:
					# Next dot is not blank. See if it is the same color dot in which case the line will complete 
					print("Non blank dot found")
					if(bitMatrix[posRow-1][posCol:posCol+3] == bitMatrix[posRow][posCol:posCol+3]):
						print("Next dot is same color")
						# Dot is same color but check if it is one of the destination dots.
						if([dotCurPositions[curIndex][0]-1,dotCurPositions[curIndex][1]] in dotCurPositions): 
							print("Line connected")
							dotCurPositions[curIndex] = copy.deepcopy(dotOrigPositions[curIndex])
							levelStatus[curIndex] = 1
							levelStatus[getTheOtherEnd(curIndex)] = 1
							if(all(levelStatus)): 
								print("It's a Game...")
								handleLevelComplete()
								loadNextLevel()
		elif (key == 'y: 1'):
			# Down arrow pressed
			# Check if an operation needs to be performed or not
			result = boundaryCheck(Direction.DOWN, dotCurPositions[curIndex])
			print("Result: ", result)
			# If operation is allowed, copy the 3 bits in current position to the bits below 
			if result:
				posRow = dotCurPositions[curIndex][0]
				posCol = int(dotCurPositions[curIndex][1]/3)*3
				print("Next dot: ", bitMatrix[posRow+1][posCol:posCol+3])
				if all(bitMatrix[posRow+1][posCol:posCol+3]):
					# All the bits are '1' so the next dot is blank
					# Before extending the line check if there is already a line with the same color. This check is needed only once when the line starts
					if (dotCurPositions[curIndex] == dotOrigPositions[curIndex]):
						clearLine(getTheOtherEnd(curIndex))
					bitMatrix[posRow+1][posCol:posCol+3] = bitMatrix[posRow][posCol:posCol+3]
					dotCurPositions[curIndex][0] = posRow + 1
				else:
					# Next dot is not blank. See if it is the same color dot in which case the line will complete 
					print("Non blank dot found")
					if(bitMatrix[posRow+1][posCol:posCol+3] == bitMatrix[posRow][posCol:posCol+3]):
						print("Next dot is same color")
						# Dot is same color but check if it is one of the destination dots.
						if([dotCurPositions[curIndex][0]+1,dotCurPositions[curIndex][1]] in dotCurPositions): 
							print("Line connected")
							dotCurPositions[curIndex] = copy.deepcopy(dotOrigPositions[curIndex])
							levelStatus[curIndex] = 1
							levelStatus[getTheOtherEnd(curIndex)] = 1
							if(all(levelStatus)): 
								print("It's a Game...")
								handleLevelComplete()
								loadNextLevel()
		elif (key == 'top'):
			# Clear the line for the current blinking dot
			clearLine(curIndex)
		elif (key == 'thumb'): 
			# Cycles through all dots and select a different dot each time the button is pressed
			# Button click to move the line will be performed on the current dot
			if (curIndex == len(dotOrigPositions)-1): curIndex = 0
			else: curIndex += 1
		elif (key == 'i'): print(key)
			# Do stuff for up button
		elif (key == 'k'): print(key)
			# Do stuff for down button
		else: print("wrong key")
		rearrangeBits()
	
keyscan()