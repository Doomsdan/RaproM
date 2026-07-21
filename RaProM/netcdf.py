"""NetCDF conversion pipeline for MRR raw files."""

from pathlib import Path
import datetime
import logging
import time

import numpy as np
from netCDF4 import Dataset, date2num

from . import processing
from .cancellation import raise_if_cancelled
from .correction import CorrectorFile
from .io import extract_archives, list_raw_files
from .processing import *

logger = logging.getLogger(__name__)


def _format_progress_bytes(position, total):
    if not total:
        return "unknown size"
    percent = min(100.0, (position / total) * 100.0)
    return f"{position / 1024 / 1024:.1f}/{total / 1024 / 1024:.1f} MB ({percent:.1f}%)"


def process_raw_file(raw_file, integration_time, antenna_height=np.nan, adjust_m=1.0, correct=True, output_dir=None, cancel_event=None):
    """Process a single MRR ``.raw`` file into a NetCDF file.

    Parameters mirror the options from the original script. The returned path is
    the generated ``*-processed.nc`` file.
    """
    NameFile = str(raw_file)
    IntTime = int(integration_time)
    h0_opt = antenna_height
    Adjust_M = float(adjust_m)
    Nw_2=[];Dm_2=[]



    count=0
    raise_if_cancelled(cancel_event)
    if correct:
        logger.info("Correcting raw file before processing: %s", NameFile)
        NameFile=CorrectorFile(NameFile)
        raise_if_cancelled(cancel_event)
        logger.info("Finished raw-file correction: %s", NameFile)
    logger.info("Processing raw file: %s", NameFile)
    source_size = Path(NameFile).stat().st_size
    source_stem = Path(NameFile).stem
    if output_dir is None:
        filenameplot = str(Path(NameFile).with_suffix('')) + '-processed'
    else:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        filenameplot = str(output_path / f"{source_stem}-processed")

    f=open(NameFile,'r')
    a=f.readline()

    Hini=f.readline()
    f.close()
    Hini=Hini.strip()
    HIcolum=np.fromstring(Hini.partition(" ")[2],dtype=int,sep=" ")#Get the height values and change to integer
    if np.isnan(h0_opt):
        HIcolum2=HIcolum
    else:
        HIcolum2=h0_opt+HIcolum

    ##    print('altures',HIcolum2)
    ##Found the parameters dv in function of the height (mrr physics equation)
    dv=[]
    for i in range(len(HIcolum2)):
        if i>=1:

            dv.append(1+3.68*10**-5*HIcolum2[i]+1.71*10**-9*HIcolum2[i]**2)
            processing.dv=dv

    speed=np.arange(0,64*fNy,fNy)
    speed21=np.arange(0,32*fNy,fNy)
    speed22=np.arange(-32*fNy,0,fNy)
    speed2=np.concatenate((speed21,speed22),axis=0)#this vector speed is to evaluate the upward



    ##Found the diameters in function of height and speed
    D=[]
    for i in range(len(dv)):
        d=[]
        for j in range(len(speed)):
            
            b=speed[j]/dv[i]

            if b>=0.002 and b<=9.37:#Condition of diameter is good for 0.109 mm< D< 6 mm
                d.append(np.log((9.65-b)/10.3)*(-1/0.6))
            else:
                d.append(np.nan)
        D.append(d)#dimension 31 x 64 in mm


    dataset=Dataset(str(filenameplot+'.nc'),mode='w',format='NETCDF4')
    dataset.description='Data processed by MRR radar'
    dataset.author='Albert Garcia Benad'+u'\xed'
    dataset.orcid='0000-0002-5560-4392 '
    if Adjust_M!=1.:
        dataset.Adjust_M='The MRR calibration constant has been adjusted with the multiplicative bias M='+str(Adjust_M)
    # if not Site:
    #     dataset.site='Undefined'
    # else:
    #     dataset.site=Site
    # if not Latitude:
    #     dataset.latitude='Undefined'

    # else:
    #     dataset.latitude=Latitude
    # if not Longitude:
    #     dataset.longitude='Undefined'
    # else:
    #     dataset.longitude=Longitude


    dataset.createDimension('DropSize',len(D[0]))

    dataset.createDimension('Height',len(HIcolum2[1:]))

    dataset.createDimension('PIA_Height',len(HIcolum2))

    dataset.createDimension('BB_Height',1)

    dataset.createDimension('time',None)
    dataset.createDimension('time_utc',None)

    nc_times=dataset.createVariable('Time','float64',('time',))
    nc_Format_times=dataset.createVariable('time_utc', 'float64', ('time_utc',))
    nc_ranges_H=dataset.createVariable('Height','f',('Height',))
    nc_ranges_H_PIA=dataset.createVariable('PIA_Height','f',('PIA_Height',))
    nc_ranges_H_BB=dataset.createVariable('BB_Height','f',('BB_Height',))
    nc_ranges_DropSize=dataset.createVariable('DropSize','f',('DropSize',))

    nc_times.units = 'UNIX Time Stamp, SECONDS SINCE 1970-01-01'
    nc_times.description='Time in unix format'

    nc_Format_times.units='seconds since 1970-01-01'
    nc_Format_times.calendar='standard'
    nc_Format_times.decription='time UTC'

    nc_ranges_H.units = 'm'
    if np.isnan(h0_opt):
        nc_ranges_H.description = 'Height a.g.l.'
    else:
        nc_ranges_H.description = 'Height a.s.l.'

    nc_ranges_H_PIA.units = 'm'
    if np.isnan(h0_opt):
        nc_ranges_H_PIA.description = 'Height a.g.l.'
    else:
        nc_ranges_H_PIA.description = 'Height a.s.l.'


    nc_ranges_H_BB.units = 'm'
    if np.isnan(h0_opt):
        nc_ranges_H_BB.description = 'Height a.g.l.'
    else:
        nc_ranges_H_BB.description = 'Height a.s.l.'




    nc_ranges_DropSize.units = 'mm'
    nc_ranges_DropSize.description = 'Size of the water drops'


    ##Found the scatter and extint sections in function of height and speed
    SigmaScatt=[]
    SigmaExt=[]
    ##    print(len(D),len(D[0]))
    for i in range(len(D)):#entry in height
        raise_if_cancelled(cancel_event)
        sig1,sig2=ScatExt(D[i],lamb)
        SigmaScatt.append(sig1)
        SigmaExt.append(sig2)
        processing.SigmaScatt=SigmaScatt
        processing.SigmaExt=SigmaExt
        




    #Start the script

    f=open(NameFile,'r')
    DataT=[]
    Mdades=[[]]
    o=0


    ########REFRACTION INDEX FROM WATERm=6.417+i*2.758 cited by Segelstein 1981
    ag_mre=6.417
    ag_mim=2.758
    Waterm = ag_mre + 1.0j * ag_mim


    #Initially parocesser parameters
    timeList=list()

    co=0


    PotCorrSum=[]


    PotSumWN=np.empty(shape=[32,64])
    PotSum=np.empty(shape=[31,64])#there is 32 height but the firts height is deleted
    NullMatrix=np.ones(np.shape(PotSum))*np.nan


    Timecount=0
    TimeCounter=0
    Cont=0
    #START THE DATA READING
    started_at = datetime.datetime.now()
    started_monotonic = time.monotonic()
    last_progress_log = started_monotonic
    logger.info("Started NetCDF conversion for %s at %s", NameFile, started_at.isoformat(timespec="seconds"))
    ContPlot=0


    while 1:
        raise_if_cancelled(cancel_event)
        line=f.readline()

        line=line.strip()
        if line=='':
            if len(PotCorrSum)!=0:
                

                TimeCounter+=1

                timeVec=timeList[0]+(IntTime*TimeCounter)
                nc_times[Timecount:Timecount+1]=timeVec#add 1 second, beacuse the timestapmps from Mrr is the last second
                nc_Format_times[Timecount:Timecount+1]=date2num(unix2date(timeVec),units=nc_Format_times.units,calendar=nc_Format_times.calendar)



                proeta=Promig(PotCorrSum)
                

                raise_if_cancelled(cancel_event)
                estat,NewMatrix,z_da,Lwc,Rr,SnowRate,w,sig,sk,Noi,DSD,NdE,Ze,Mov,velTur,snr,kur,PiA_par,NW,DM,PiA=Process(proeta,Harray[1:],timeVec,D)
                raise_if_cancelled(cancel_event)
                bb_bot,bb_top=BB(w,Ze,Harray[1:])
                estat,NW,DM,Lwc,Rr=CheckType(estat,bb_bot,bb_top,DeltaH,NW,DM,Lwc,Rr,sk,Ze,kur,snr,sig,w)
                z_da,Lwc,Rr,NW,DM,DSD,NdE,PiA_da=Rain_Par(estat,z_da,Lwc,Rr,NW,DM,NewMatrix,D,DSD,NdE,Harray[1:],w,PiA)
                Z_da=[]
                for n in range(len(z_da)):
                    
                    Z_da.append(z_da[n]-10.*np.log10(PiA_da[n+1]))
                    
                

                nc_state[Timecount,:]=np.array(np.ma.masked_invalid(estat),dtype='f')
                nc_w[Timecount,:]=np.array(np.ma.masked_invalid(w),dtype='f')
                nc_sig[Timecount,:]=np.array(np.ma.masked_invalid(sig),dtype='f')
                nc_sk[Timecount,:]=np.array(np.ma.masked_invalid(sk),dtype='f')
                nc_kur[Timecount,:]=np.array(np.ma.masked_invalid(kur),dtype='f')

                nc_PIA[Timecount,:]=np.array(np.ma.masked_invalid(10.*np.log10(PiA_da)),dtype='f')
                nc_PIA_all[Timecount,:]=np.array(np.ma.masked_invalid(10.*np.log10(PiA)),dtype='f')

                nc_bb_bot[Timecount,:]=np.array(np.ma.masked_invalid(bb_bot),dtype='f')
                nc_bb_top[Timecount,:]=np.array(np.ma.masked_invalid(bb_top),dtype='f')
                
                
                nc_LWC[Timecount,:]=np.array(np.ma.masked_invalid(Lwc),dtype='f')
                nc_RR[Timecount,:]=np.array(np.ma.masked_invalid(Rr),dtype='f')

                nc_nw[Timecount,:]=np.array(np.ma.masked_invalid(NW),dtype='f')
                nc_dm[Timecount,:]=np.array(np.ma.masked_invalid(DM),dtype='f')
                if ~np.isnan(DM).all():
                    Nw_2.append(NW)
                    Dm_2.append(DM)
                
                nc_Z_da[Timecount,:]=np.array(np.ma.masked_invalid(Z_da),dtype='f')
                nc_Z_DA[Timecount,:]=np.array(np.ma.masked_invalid(z_da),dtype='f')
                nc_Z_e[Timecount,:]=np.array(np.ma.masked_invalid(Ze),dtype='f')
                

                nc_N_daTH[Timecount,:,:]=np.array(np.ma.masked_invalid(np.log10(NdE)),dtype='f')
                
                nc_SnowR[Timecount,:]=np.array(np.ma.masked_invalid(SnowRate),dtype='f')
                nc_Noi[Timecount,:]=np.array(np.ma.masked_invalid(Noi),dtype='f')
                nc_SNR[Timecount,:]=np.array(np.ma.masked_invalid(snr),dtype='f')
                nc_N_da[Timecount,:]=np.array(np.ma.masked_invalid(DSD),dtype='f')

                
               
            break


        
            
        columns=line.split()

        Date=columns[1] 

        
        dat = datetime.datetime(year = 2000+int(Date[0:2]), month = int(Date[2:4]), day = int(Date[4:6]), hour = int(Date[6:8]), minute = int(Date[8:10]), second = int(Date[10:12]))
        
        dat=int(date2unix(dat))

        timeList.append(dat-int(unix2date(dat).second))#fixs the time at 0 seconds
        TypeDate=columns[2] 
        DVS=columns[4] 
        DSN=columns[6] #serial number
        BW=columns[8] #Witdh band
        CC=int(columns[10]) #Calibration constant
        MDQ=columns[12:15] 
                        

        TypeFile=columns[16] 

        

        #Read the heigh parameters (second line from raw file)
        H=f.readline()
        H=H.strip()
        Hcolum=np.fromstring(H.partition(" ")[2],dtype=int,sep=" ")#Get the height values and change to integer
        if np.isnan(h0_opt):
            Harray=Hcolum
        else:
            Harray=h0_opt+Hcolum
    ##        Harray=np.fromiter(Hcolum,dtype=int)
        DeltaH=Harray[5]-Harray[4]#Height difference

        #Read the tranference function (third line from raw file)
        FT=f.readline()
        FT=FT.strip()
        FTarray=np.fromstring(FT.partition(" ")[2],dtype=float,sep=" ")
        vectorV=np.arange(0,64*fNy,fNy)
        

        #constant value to conevrt F to f, include all constants, and the possible correction from M
        Cte=DeltaH*float(CC)/(Adjust_M*10**20)
        processing.Cte=Cte
        
        
        #Read the values F from file
        
        FQ=[]
        DataT=[]
        
        
        Number_bins=64#is the number of heights from file
        for j in range(Number_bins):
            raise_if_cancelled(cancel_event)
            Data=f.readline()
            Data=Data.strip()
            Data=Data.split()
            Dades1=map(int,Data[1:len(Data)]) #extract the title for eac line F00, F01, etc
            Dades=np.fromiter(Dades1,dtype=int)

            
            FQ.append(Data[0])
            DataT.append(Dades)
            
        data_matrix=np.asarray(DataT,dtype=float)
        height_indices=np.arange(1,len(Harray),dtype=float)
        quotients=FTarray[1:]/np.square(height_indices)
        Pot=(data_matrix[:,1:].T/quotients[:,None])#pot is the spectra potence (v,i) except by muliply a constant where eac array is a column, or gate height


        hcor=np.asarray(Harray[1:])
        


        timeVec=timeList[0]+(IntTime*TimeCounter)
        if (dat-timeVec)>=IntTime:
            
            TimeCounter+=1
            timeVec=timeList[0]+(IntTime*TimeCounter)
            if len(PotCorrSum)==0:
                proeta=NullMatrix
            else:


                proeta=Promig(PotCorrSum)

            nc_times[Timecount:Timecount+1]=timeVec#add 1 second, beacuse the timestapmps from Mrr is the last second
            nc_Format_times[Timecount:Timecount+1]=date2num(unix2date(timeVec),units=nc_Format_times.units,calendar=nc_Format_times.calendar)
            nc_ranges_H[:]=np.array(Harray[1:],dtype='f4')
            nc_ranges_H_PIA[:]=np.array(Harray,dtype='f4')
            nc_ranges_DropSize[:]=np.array(np.ma.masked_invalid(D[0]),dtype='f')
            ncShape2D = ('time_utc','Height',)
            ncShape2D_BB = ('time_utc','BB_Height',)
            ncShape2D_PIA = ('time_utc','PIA_Height',)#PIA starts in h=0, for this has 32 heights
            ncShape3D = ('time','Height','DropSize',)
            if Timecount==0:
                ##################create netcdf############

                nc_w=dataset.createVariable('W','f',ncShape2D)
                nc_w.description='Fall speed with aliasing correction'
                nc_w.units='m/s'
                

                nc_sig=dataset.createVariable('spectral width','f',ncShape2D)
                nc_sig.description='Spectral width of the dealiased velocity distribution'
                nc_sig.units='m/s'
                

                nc_sk=dataset.createVariable('Skewness','f',ncShape2D)
                nc_sk.description='Skewness of the spectral reflectivity with dealiasing'
                nc_sk.units='none'

                nc_kur=dataset.createVariable('Kurtosis','f',ncShape2D)
                nc_kur.description='Kurtosis of the spectral reflectivity with dealiasing'
                nc_kur.units='none'

                nc_PIA=dataset.createVariable('PIA','f',ncShape2D_PIA)
                nc_PIA.description='Path Integrated Attenuation calculated using only liquid hydrometeors according to hydrometeor type classification'
                nc_PIA.units='dB'

                nc_PIA_all=dataset.createVariable('PIA_all','f',ncShape2D_PIA)
                nc_PIA_all.description='Path Integrated Attenuation calculated assuming all hydrometeors are in liquid phase regardless of hydrometeor type classification'
                nc_PIA_all.units='dB'

                nc_state=dataset.createVariable('Type','f',ncShape2D)
                nc_state.description='Predominant hydrometeor type numerical value where possible values are: -20 (hail), -15 (graupel), -10 (snow), 0 (mixed), 5 (drizzle), 10 (rain) and 20 (unknown precipitation)'
                nc_state.units=''
                

                

                nc_LWC=dataset.createVariable('LWC','f',ncShape2D)
                nc_LWC.description='Liquid Water Content calculated using only liquid hydrometeors according to hydrometeor type classification'
                nc_LWC.units='g m-3'
                

                nc_RR=dataset.createVariable('RR','f',ncShape2D)
                nc_RR.description='Rain Rate calculated using only liquid hydrometeors according to hydrometeor type classification'
                nc_RR.units='mm hr-1'

                nc_SnowR=dataset.createVariable('SR','f',ncShape2D)
                nc_SnowR.description='Snow Rate'
                nc_SnowR.units='mm hr-1'
                
                
                nc_Z_DA=dataset.createVariable('Z','f',ncShape2D)
                nc_Z_DA.description='Radar reflectivity calculated using only liquid hydrometeors according to hydrometeor type classification'
                nc_Z_DA.units='dBZ'

                nc_Z_da=dataset.createVariable('Za','f',ncShape2D)
                nc_Z_da.description='Attenuated radar reflectivity calculated using only liquid hydrometeors according to hydrometeor type classification'
                nc_Z_da.units='dBZ'

                nc_Z_e=dataset.createVariable('Ze','f',ncShape2D)
                nc_Z_e.description='Equivalent radar reflectivity'
                nc_Z_e.units='dBZ'

                               
                nc_N_da=dataset.createVariable('N(D)','f',ncShape2D)
                nc_N_da.description='Drop Size Distribution calculated using only liquid hydrometeors according to hydrometeor type classification'
                nc_N_da.units='log10(m-3 mm-1)'

                nc_N_daTH=dataset.createVariable('N(D) in function of time and height','f',ncShape3D)
                nc_N_daTH.description='Drop Size Distribution in function of time and height calculated using only liquid hydrometeors according to hydrometeor type classification'
                nc_N_daTH.units='log10(m-3 mm-1)'
                
                nc_SNR=dataset.createVariable('SNR','f',ncShape2D)
                nc_SNR.description='Signal to noise ratio from signal without dealiasing '
                nc_SNR.units='dB'

                nc_Noi=dataset.createVariable('Noise','f',ncShape2D)
                nc_Noi.description='Noise from spectra reflectivity '
                nc_Noi.units='m-1'

                nc_nw=dataset.createVariable('Nw','f',ncShape2D)
                nc_nw.description='Intercept of the gamma distribution normalized to the Liquid Water Content calculated using only liquid hydrometeors according to hydrometeor type classification'
                nc_nw.units='log10(mm-1 m-3)'

                nc_dm=dataset.createVariable('Dm','f',ncShape2D)
                nc_dm.description='Mean mass-weighted raindrop diameter calculated using only liquid hydrometeors according to hydrometeor type classification'
                nc_dm.units='mm'


                nc_bb_bot=dataset.createVariable('BB_bottom','f',ncShape2D_BB)
                if np.isnan(h0_opt):
                    nc_bb_bot.description='Bright Band bottom height a.g.l.'
                else:
                    nc_bb_bot.description='Bright Band bottom height a.s.l.'
                            
                nc_bb_bot.units='m'

                nc_bb_top=dataset.createVariable('BB_top','f',ncShape2D_BB)
                if np.isnan(h0_opt):
                    nc_bb_top.description='Bright Band top height a.g.l.'
                else:
                    nc_bb_top.description='Bright Band top height a.s.l.'
                
                nc_bb_top.units='m'


            PotCorrSum=[]#empty the array    
            raise_if_cancelled(cancel_event)
            estat,NewMatrix,z_da,Lwc,Rr,SnowRate,w,sig,sk,Noi,DSD,NdE,Ze,Mov,velTur,snr,kur,PiA_par,NW,DM,PiA=Process(proeta,Harray[1:],timeVec,D)
            raise_if_cancelled(cancel_event)
            bb_bot,bb_top=BB(w,Ze,Harray[1:])
            estat,NW,DM,Lwc,Rr=CheckType(estat,bb_bot,bb_top,DeltaH,NW,DM,Lwc,Rr,sk,Ze,kur,snr,sig,w)
            z_da,Lwc,Rr,NW,DM,DSD,NdE,PiA_da=Rain_Par(estat,z_da,Lwc,Rr,NW,DM,NewMatrix,D,DSD,NdE,Harray[1:],w,PiA)

            Z_da=[]
            for n in range(len(z_da)):
                
                Z_da.append(z_da[n]-10.*np.log10(PiA_da[n+1]))
                

                

            nc_state[Timecount,:]=np.array(np.ma.masked_invalid(estat),dtype='f')
            nc_w[Timecount,:]=np.array(np.ma.masked_invalid(w),dtype='f')
            nc_sig[Timecount,:]=np.array(np.ma.masked_invalid(sig),dtype='f')
            nc_sk[Timecount,:]=np.array(np.ma.masked_invalid(sk),dtype='f')
            nc_kur[Timecount,:]=np.array(np.ma.masked_invalid(kur),dtype='f')
            nc_PIA[Timecount,:]=np.array(np.ma.masked_invalid(10.*np.log10(PiA_da)),dtype='f')
            nc_PIA_all[Timecount,:]=np.array(np.ma.masked_invalid(10.*np.log10(PiA)),dtype='f')

            nc_N_daTH[Timecount,:,:]=np.array(np.ma.masked_invalid(np.log10(NdE)),dtype='f')

            nc_nw[Timecount,:]=np.array(np.ma.masked_invalid(NW),dtype='f')
            nc_dm[Timecount,:]=np.array(np.ma.masked_invalid(DM),dtype='f')
            if ~np.isnan(DM).all():
                    Nw_2.append(NW)
                    Dm_2.append(DM)

            nc_bb_bot[Timecount,:]=np.array(np.ma.masked_invalid(bb_bot),dtype='f')
            nc_bb_top[Timecount,:]=np.array(np.ma.masked_invalid(bb_top),dtype='f')
                            
            nc_LWC[Timecount,:]=np.array(np.ma.masked_invalid(Lwc),dtype='f')
            nc_RR[Timecount,:]=np.array(np.ma.masked_invalid(Rr),dtype='f')

            nc_Z_DA[Timecount,:]=np.array(np.ma.masked_invalid(z_da),dtype='f')
            nc_Z_da[Timecount,:]=np.array(np.ma.masked_invalid(Z_da),dtype='f')
            nc_Z_e[Timecount,:]=np.array(np.ma.masked_invalid(Ze),dtype='f')
            
            
            nc_SnowR[Timecount,:]=np.array(np.ma.masked_invalid(SnowRate),dtype='f')
            nc_Noi[Timecount,:]=np.array(np.ma.masked_invalid(Noi),dtype='f')
            nc_SNR[Timecount,:]=np.array(np.ma.masked_invalid(snr),dtype='f')
            nc_N_da[Timecount,:]=np.array(np.ma.masked_invalid(DSD),dtype='f')

            

            Timecount=Timecount+1
            now = time.monotonic()
            if Timecount == 1 or now - last_progress_log >= 30:
                logger.info(
                    "Still processing %s: read %s, generated %s time interval(s), elapsed %.1f min",
                    NameFile,
                    _format_progress_bytes(f.tell(), source_size),
                    Timecount,
                    (now - started_monotonic) / 60.0,
                )
                last_progress_log = now
            elif Timecount % 10 == 0:
                logger.debug("Processed %s time interval(s) from %s", Timecount, NameFile)
            
            
        PotCorrSum.append(Pot)#add matrix

    f.close()
    if ~np.isnan(Dm_2).all() and ~np.isnan(Nw_2).all():
        dm_ax,nw_ax,PrepTypeC=PrepType(Dm_2,Nw_2)
        dataset.createDimension('Dm_ax',len(dm_ax))
        dataset.createDimension('Nw_ax',len(nw_ax))

        nc_ranges_Dm=dataset.createVariable('Dm_ax','f',('Dm_ax',))
        nc_ranges_Nw=dataset.createVariable('Nw_ax','f',('Nw_ax',))
        
        nc_ranges_Dm.description = 'Mean diameter axes to rainfall type'
        nc_ranges_Dm.units = '(mm)'
        
        nc_ranges_Nw.description = 'Intecept parameter axes to Rainfall type'
        nc_ranges_Nw.units = 'log(m-3 mm-1)'

        nc_ranges_Dm[:]=np.array(dm_ax,dtype='f4')
        nc_ranges_Nw[:]=np.array(nw_ax,dtype='f4')



        nc_TypePrecipitation=dataset.createVariable('TyPrecipi','f',('Dm_ax','Nw_ax',))
        nc_TypePrecipitation.description='Precipitation regime numerical value where possible values are: 5 (convective), 0 (transition) and -5 (stratiform) calculated using only liquid hydrometeors according to hydrometeor type classification'##, following the method of https://doi.org/10.1016/j.atmosres.2015.04.011'
        nc_TypePrecipitation.units='none'

        nc_TypePrecipitation[:,:]=np.array(np.ma.masked_invalid(PrepTypeC),dtype='f')
    dataset.close()
    output_path = str(Path(filenameplot + '.nc'))
    logger.info(
        "Finished NetCDF conversion for %s: %s (%s time interval(s))",
        NameFile,
        output_path,
        Timecount,
    )
    return output_path


def _processed_output_candidates(raw_file, output_dir=None, correct=True):
    raw_path = Path(raw_file)
    if output_dir is None:
        output_path = raw_path.parent
        candidates = [output_path / f"{raw_path.stem}-processed.nc"]
        if correct:
            candidates.append(raw_path.parent / "CorrectedRaw" / f"{raw_path.stem}-corrected-processed.nc")
        return candidates

    output_path = Path(output_dir)
    candidates = [output_path / f"{raw_path.stem}-processed.nc"]
    if correct:
        candidates.append(output_path / f"{raw_path.stem}-corrected-processed.nc")
    return candidates


def _already_processed(raw_file, output_dir=None, correct=True):
    return any(path.exists() for path in _processed_output_candidates(raw_file, output_dir, correct))


def prepare_directory(root, output_dir=None, correct=True):
    """Extract archives below *root* and return unprocessed raw files."""
    root_path = Path(root)
    extract_archives(
        root_path,
        should_extract=lambda destination: destination.suffix.lower() != ".raw" or not _already_processed(destination, output_dir, correct),
    )
    raw_files = list_raw_files(root_path)
    unprocessed = []
    for raw_file in raw_files:
        if _already_processed(raw_file, output_dir, correct):
            logger.info("Skipping already processed raw file: %s", raw_file)
            continue
        unprocessed.append(raw_file)
    return unprocessed, raw_files


def process_directory(root, integration_time, antenna_height=np.nan, adjust_m=1.0, correct=True, output_dir=None, cancel_event=None):
    """Extract archives and process every unprocessed ``.raw`` file in *root*."""
    root_path = Path(root)
    raw_files, all_raw_files = prepare_directory(root_path, output_dir, correct)
    logger.info("Found %s raw file(s) in %s", len(all_raw_files), root_path)
    logger.info("Generated NetCDF files use the source raw filename with a '-processed.nc' suffix.")
    outputs = []
    for raw_file in raw_files:
        raise_if_cancelled(cancel_event)
        if cancel_event is None:
            outputs.append(process_raw_file(raw_file, integration_time, antenna_height, adjust_m, correct, output_dir))
        else:
            outputs.append(
                process_raw_file(
                    raw_file,
                    integration_time,
                    antenna_height,
                    adjust_m,
                    correct,
                    output_dir,
                    cancel_event=cancel_event,
                )
            )
    return outputs
