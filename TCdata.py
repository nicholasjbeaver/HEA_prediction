from tc_python import *
from itertools import combinations
import bisect
import csv
import os
with TCPython() as start:

	#hardcode folder here
	folder=r"C:\Users\nmelisso\NewFolder"

	def MakeTable(PropDiag,path):
		table=[]
		header=["Temperature"]
		for idx,group in enumerate(PropDiag.values()):
			header.append(group.label)
			currenttemps=[]
			if idx==0:
				for i,j in enumerate(group.x):
					if j in currenttemps:
						table[[k[0] for k in table].index(j)][-1]+=group.y[i]
					else:
						table.append([j,group.y[i]])
					currenttemps.append(j)
			else:
				for i,j in enumerate(group.x):
					tabletemps=[k[0] for k in table]
					if j in tabletemps:
						if j in currenttemps:
							table[tabletemps.index(j)][-1]+=group.y[i]
						else:
							table[tabletemps.index(j)].append(group.y[i])
					else:
						newtemp=bisect.bisect(tabletemps,j)
						table.insert(newtemp,[0]*(idx+2))
						table[newtemp][0]=j
						table[newtemp][-1]=group.y[i]
					currenttemps.append(j)
				for i in table:
					if len(i)<idx+2:
						i.append(0)
			print(group.label)
			print(group.x)
			print(group.y)
		print(table)
		with open(path, 'w', newline='') as file:
			writer = csv.writer(file)
			writer.writerow(header)
			for i,j in enumerate(table):
				writer.writerow(table[i])

	def alloy(Elem,path,bookmark1=0,bookmark2=0):
		debug=0
		for NumElem in range(bookmark1,len(Elem)):
			print(NumElem)
			if NumElem==0:
				for NumComb,CombElem in enumerate(Elem[bookmark2:]):
					csv.writer(open(path+r"\aaabookmark.csv",'w')).writerow([NumElem,NumComb+bookmark2])
					property_diagram = (
						start.
						select_database_and_elements("TCHEA4", [CombElem]).
						get_system().
						with_property_diagram_calculation().
						with_axis(CalculationAxis(ThermodynamicQuantity.temperature()).
							set_min(380).
							set_max(2800)).
						calculate().
						get_values_grouped_by_quantity_of(ThermodynamicQuantity.temperature(),
						ThermodynamicQuantity.mole_fraction_of_a_phase("ALL"))
					)
					newPath=path+"\\"+CombElem+".csv"
					print(CombElem)
					MakeTable(property_diagram,newPath)
			else:
				comblist=list(combinations(Elem,NumElem+1))
				if bookmark1==NumElem:
					comblist=list(combinations(Elem,NumElem+1))[bookmark2:]
				for NumComb,CombElem in enumerate(comblist):
					csv.writer(open(path+r"\aaabookmark.csv",'w')).writerow([NumElem,NumComb+bookmark2])
					a = (
						start.
						select_database_and_elements("TCHEA4", CombElem).
						get_system().
						with_property_diagram_calculation().
						with_axis(CalculationAxis(ThermodynamicQuantity.temperature()).
							set_min(380).
							set_max(2800))
					)
					for i in range(NumElem):
						a = a.set_condition(ThermodynamicQuantity.mole_fraction_of_a_component(CombElem[i+1]), round(1/(NumElem+1),3))
					property_diagram = (
						a.calculate().
						get_values_grouped_by_quantity_of(ThermodynamicQuantity.temperature(),
						ThermodynamicQuantity.mole_fraction_of_a_phase("ALL"))
					)
					newPath=path+"\\"+CombElem[0]
					for i in range(NumElem):
						newPath+="_"+CombElem[i+1]
					newPath+=".csv"
					print(CombElem)
					MakeTable(property_diagram,newPath)
					debug=debug+1

		print(debug)

	cont=True
	elements=[]
	b1=0
	b2=0
	while(cont):
		inp=input("type \'s\' for skip, \'b\' for bookmark, \'f\' for folder, or enter for continue, or input element\n")
		if inp=="continue" or inp=="":
			blist=list(csv.reader(open(folder+r"\aaabookmark.csv",'r')))
			b1=int(blist[0][0])
			b2=int(blist[0][1])
			print(str(b1)+"\n"+str(b2))
			cont=False
		elif inp=="bookmark" or inp=="b":
			b1=input("input bookmark 1\n")
			b2=input("input bookmark 2\n")
			csv.writer(open(folder+r"\aaabookmark.csv",'w')).writerow([b1,b2])
		elif inp=="skip" or inp=="s":
			blist=list(csv.reader(open(folder+r"\aaabookmark.csv",'r')))
			b1=int(blist[0][0])
			b2=int(blist[0][1])
			if elements!=[]:
				csv.writer(open(folder+r"\aaaelements.csv",'w')).writerow(elements)
			else:
				elements=list(csv.reader(open(folder+r"\aaaelements.csv",'r')))[0]
			if b2<len(list(combinations(elements,b1+1)))-1:
				b2+=1
			else:
				b1+=1
				b2=0
			print(str(b1)+"\n"+str(b2))
			cont=False
		elif inp=="folder" or inp=="f":
			folder=input("enter your folder path\n")
		else:
			elements.append(inp)
	if not os.path.isfile(folder+r"\aaabookmark.csv"):
		csv.writer(open(folder+r"\aaabookmark.csv",'w')).writerow([0,0])
	if elements!=[]:
		csv.writer(open(folder+r"\aaaelements.csv",'w')).writerow(elements)
	else:
		elements=list(csv.reader(open(folder+r"\aaaelements.csv",'r')))[0]
	print(elements)
	alloy(elements,folder,b1,b2)
