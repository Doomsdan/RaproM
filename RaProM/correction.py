"""Raw MRR file correction utilities."""

###script for correct the raw data from Mrr2 radar of Mettek
###Autor: Albert Garcia Benadi
###ORCID: 0000-0002-5560-4392
##
##202504- This version is adapted to python 3.13


import numpy as np
import calendar
import datetime
import logging
from pathlib import Path

##import matplotlib.dates as mdates

logger = logging.getLogger(__name__)

def date2unix(date):
    return calendar.timegm(date.timetuple())
def unix2date(unix):
    return datetime.datetime.utcfromtimestamp(unix)

def CorrectorFile(fid, output_dir=None):
    NameFile=fid
    source_path = Path(NameFile).resolve()
    if output_dir is None:
        output_path = source_path.parent / "CorrectedRaw"
    else:
        output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    OutNameFile=str(output_path / f"{source_path.stem}-corrected")

    FileCorre=str(output_path / f"{source_path.stem}-correctedRepetition.raw") #create a new file

    FileCorre2=str(output_path / f"{source_path.stem}-correctedErrors.raw") #create a new file

    FileCorre3=str(output_path / f"{source_path.stem}-correctedJumps.raw") #create a new file
    
##    f1=open(FileCorre,'w+')

    f=open(NameFile,'r', errors='ignore')
    file_length = len(f.read().split('\n'))
    totallines=(file_length-7)/67
    logger.debug("Starting raw file correction for %s; estimated records: %s", source_path, totallines)
    
    m=0
    timeList=list()
    f.close()


########CHECKING FOR HEADERS REPETITION
    f=open(NameFile,'r', errors='ignore')
    f1=open(FileCorre,'w+')
    
    
    cond=1
    CountM=0#number repetittion
    countM=0
    while cond:
        
        line=f.readline()
        if line=='':
            break

    
        line2=line.strip()
        columns=line2.split()

        valor=columns[0]

                
        
        if valor[0]=='M' or valor[0]=='H':
            if valor[0]=='M':
                line1=line
                countM+=1
            if valor[0]=='H':
                Line=line1+line
                f1.write(Line)
                CountM=countM-1
                countM=0
        else:
            Line=line
            f1.write(Line)
##        print('rep header ',CountM)
##        print('linea ',line)

        
    f1.close()
    f.close()
########CHECKING FOR ERRORS IN THE RAW FILE
    f=open(FileCorre,'r')
    f1=open(FileCorre2,'w+')
    
    cond=1
    lineCount=0
    LineCount=0
    countF=0
    
    TotalLinesFile=0
    while cond:
        
        line=f.readline()
        TotalLinesFile+=1#lines counter
        if line=='':
            
            break

    
    
        line2=line.strip()
        columns=line2.split()

        valor=columns[0]

                
        
        if valor[0]=='M' or valor[0]=='H' or valor[0]=='T' or valor[0]=='F':
            LineCount+=1
            if valor[0]=='M':
                if countF!=64 or countF==0:
                    
                    if countF!=0:
                        lineCount=lineCount+LineCount#sumo el nombre de lines
                    
                    
                else:
                    f1.write(Line)
                
                Line=line
                LineCount=0#reset numero lines
                countF=0#rest el contador de les F
                

            else:
                Line=Line+line
                

            
            if valor[0]=='F':
                countF+=1
            if valor[0]=='T':
                LineTF=line
        else:
            
            
            if valor[0]=='C' and len(columns)>4:

                if columns[4]=='"TF':
                    Line=Line+LineTF
##                    print(line[25:-3])
##                    print(TotalLinesFile)
                else:
                    lineCount+=1
            else:
                lineCount+=1
            
            
    
    f1.close()
    f.close()
########CHECKING FOR JUMPS TIME FOR THE SYNCHRONIZATION

    f=open(FileCorre2,'r')
    f1=open(FileCorre3,'w+')
    cond=1

    while cond:
        
        line=f.readline()
        if line=='':
            break

    
        line2=line.strip()
        columns=line2.split()
    
        if len(columns)==1:
            longStr=2
        else:
            Date=columns[1]
            longStr=len(str(Date))

       
        
            
        
        if len(timeList)==0:
            dat = datetime.datetime(year = 2000+int(Date[0:2]), month = int(Date[2:4]), day = int(Date[4:6]), hour = int(Date[6:8]), minute = int(Date[8:10]), second = int(Date[10:12]))
            dat=int(date2unix(dat))
            for j in range(67):
                
                f1.write(line)
                
                if j<66:
                    line=f.readline()
            timeList.append(dat)
        else:

            if longStr==12:
                dat = datetime.datetime(year = 2000+int(Date[0:2]), month = int(Date[2:4]), day = int(Date[4:6]), hour = int(Date[6:8]), minute = int(Date[8:10]), second = int(Date[10:12]))
                dat=int(date2unix(dat))
                if timeList[-1]<dat:
                    
                    for j in range(67):
                        f1.write(line)
                        if j<66:
                            line=f.readline()
                    timeList.append(dat)

            
            else:
                m=m+1

          
    f1.close()
    f.close()
######    SELECT THE CORRECTED OUTPUT IF CORRECTIONS WERE NEEDED. m is for jumps correction, lineCount for error corrections and CountM for repetitions header
    intermediate_files = [Path(FileCorre), Path(FileCorre2), Path(FileCorre3)]
    final_corrected_path = Path(OutNameFile+'.raw')
    corrected_source = None
    if m==0 and lineCount==0 and CountM==0:#file correct
        OutName=NameFile
    if m==0 and lineCount!=0 and CountM==0:#file with errors in lines
        corrected_source = Path(FileCorre2)
    if m==0 and lineCount==0 and CountM!=0:#file with header repetition
        corrected_source = Path(FileCorre)
    if m!=0 and lineCount==0 and CountM==0:# file with time jumps backward
        corrected_source = Path(FileCorre3)

    if m!=0 and lineCount!=0 and CountM==0:#file with time jumps backward and errors in lines
        corrected_source = Path(FileCorre3)

    if m==0 and lineCount!=0 and CountM!=0:#file with header repetition and errors in lines
        corrected_source = Path(FileCorre2)

    if m!=0 and lineCount==0 and CountM!=0:#file with time jumps backward and header repetition
        corrected_source = Path(FileCorre3)

    if m!=0 and lineCount!=0 and CountM!=0:#file with all problems
        corrected_source = Path(FileCorre3)

    if corrected_source is not None:
        corrected_source.replace(final_corrected_path)
        OutName = str(final_corrected_path)
        logger.info("Wrote corrected raw file: %s", final_corrected_path)
    else:
        logger.info("No corrections needed for %s", source_path)

    for temp_file in intermediate_files:
        if temp_file != final_corrected_path:
            temp_file.unlink(missing_ok=True)

    logger.info(
        "Correction ratio for %s: %.2f%% (%s rows deleted from %s)",
        NameFile,
        round(100.*(m+lineCount+CountM)/TotalLinesFile,2),
        m+lineCount+CountM,
        TotalLinesFile,
    )
    logger.debug("Rows deleted by header repetition: %s", CountM)
    logger.debug("Rows deleted by malformed lines: %s", lineCount)
    logger.debug("Rows deleted by backward time jumps: %s", m)
##    print('total lines',TotalLinesFile,' and deleted ',m+lineCount)
    return OutName
