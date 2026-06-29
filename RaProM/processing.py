"""Core numerical processing routines for RaProM."""

import calendar
import datetime
from functools import lru_cache
from math import e

import miepython as mp
import numpy as np


@lru_cache(maxsize=8192)
def _mie_efficiencies_cached(m_real, m_imag, x):
    m = complex(m_real, m_imag)
    if hasattr(mp, "mie"):
        return mp.mie(m, x)
    return mp.efficiencies_mx(m, x)


def mie_efficiencies(m, x):
    """Return Mie efficiencies across supported miepython versions."""
    if np.ndim(x)==0:
        return _mie_efficiencies_cached(float(np.real(m)), float(np.imag(m)), float(x))
    if hasattr(mp, "mie"):
        return mp.mie(m, x)
    return mp.efficiencies_mx(m, x)


def PrepType(dm,nw):
##    convert the matrix dm, nw in  linear vector
    Dm=np.asarray(dm,dtype=float).ravel()
    Nw=np.asarray(nw,dtype=float).ravel()
    valid=(~np.isnan(Dm)) & (~np.isnan(Nw))
    Dm=Dm[valid]
    Nw=Nw[valid]

    Dm2=np.round(Dm,1)
    Nw2=np.round(Nw,1)
    Y2=np.round(Nw-(6.3-1.6*Dm),1)#thurai(2016) index from https://doi.org/10.1016/j.atmosres.2015.04.011
                       

    Dm_axes=np.arange(np.min(Dm2),np.max(Dm2),.1)
    Nw_axes=np.arange(np.min(Nw2),np.max(Nw2),.1)
    dm_axes=np.round(Dm_axes,1).tolist()
    nw_axes=np.round(Nw_axes,1).tolist()

    Matrix=np.ones((len(dm_axes),len(nw_axes)))*np.nan
##    Create the matrix results Stra, Trans and Convective
    dm_index={value:index for index,value in enumerate(dm_axes)}
    nw_index={value:index for index,value in enumerate(nw_axes)}
    for dm_value,nw_value,y_value in zip(Dm2,Nw2,Y2):
        i=dm_index.get(dm_value)
        k=nw_index.get(nw_value)
        if i is not None and k is not None:
            Matrix[i,k]=y_value

##    Matrix is the matrix with the values de index Thurai(2016) https://doi.org/10.1016/j.atmosres.2015.04.011
##now give the values from precypitation type where convective is 1, transition is 0 and stratiform is -1
    valid_matrix=~np.isnan(Matrix)
    Matrix[valid_matrix & (np.abs(Matrix)<=0.3)]=0.#transtition
    Matrix[valid_matrix & (Matrix<-0.3)]=-5.#stratiform
    Matrix[valid_matrix & (Matrix>0.3)]=5.#convective
    

    return dm_axes,nw_axes,Matrix

def date2unix(date):
    return calendar.timegm(date.timetuple())
def unix2date(unix):
    return datetime.datetime.utcfromtimestamp(unix)

def smooth(y, box_pts):
    box = np.ones(box_pts)/box_pts
    y_smooth = np.convolve(y, box, mode='same')
    return y_smooth
def Rain_Par(state,Z,LWC,RR,Nw,Dm,NewM,D,N_da,NdE,he,w,Pia):
    PIA=[];Nde=[];he=np.asarray(he)
    PIA.append(1.)
    roW=10**6 #water density g/m3
    for m in range(np.size(state)):
        if state[m]==10 or state[m]==5:#rain case
            PIA.append(Pia[m+1])
            dif=[]#diference between diameters for N
            dif2=[]#diference between diameters for Z
            nde=[]
            indexFinded=[]
            for n in range(len(D[m])):
                if n==0 or n==len(D[m])-1:
                    if n==0:
                        dif2.append(D[m][n+1]-D[m][n])
                        dif.append(D[m][n+1]-D[m][n])
                    if n==len(D[m])-1:
                        dif.append(abs(D[m][n-1]-D[m][n]))
                        dif2.append(abs(D[m][n]-D[m][n-1]))
                else:
                    dif2.append(abs((D[m][n+1]-D[m][n])))
                    dif.append(abs((D[m][n+1]-D[m][n-1]))/2.)
                    
                        
                

                EtaV=NewM[m][64:64*2]#interval for water choosed
                value=6.18*EtaV[n]*dv[m]*e**(-1*0.6*D[m][n])#units m-1 mm-1
                s=SigmaScatt[m][n]
                value2=(10**6)*(value/s)#N in m-3 mm-1
                nde.append(value2)#units mm-1 m-3


                
            LastN=nde
            NdE[m]=LastN

            value=np.nansum(np.prod([np.power(D[m],6),LastN,dif2],axis=0))
            value2=np.nansum(np.prod([np.power(D[m],3),LastN,dif2],axis=0))
            value3=np.nansum(np.prod([np.power(D[m],3),LastN,dif2],axis=0))*w[m]
            value4=np.nansum(np.prod([np.power(D[m],4),LastN,dif2],axis=0))
                
            if np.nansum(nde)<=0.:
                N_da[m]=(np.nan)
            else:
                N_da[m]=(np.log10(np.nansum(LastN)))


                        
                        
            if value<=0. or np.isnan(value):
                Z[m]=(np.nan)
            else:
                Z[m]=(10*np.log10(value))
            if value2==0.:
                LWC[m]=(np.nan)
            else:
                LWC[m]=(roW*value2*(np.pi/6.)*(10**-9))
            if value3==0.:
                RR[m]=np.nan
            else:
                RR[m]=(value3*(np.pi/6.)*(10**-9)*1000.*3600.)
            if value4==0:
                Dm[m]=np.nan
                Nw[m]=np.nan
            else:
                Dm[m]=(value4/value2)
                Nw[m]=(np.log10(256.*(roW*value2*(np.pi/6.))/ (np.pi*roW*(value4/value2)**4)))#units m-3 mm-1
        else:
            PIA.append(np.nan)



    return Z,LWC,RR,Nw,Dm,N_da,NdE,PIA
def CheckType(Type,BB_bot,BB_top,Deltah,NW,DM,LWC,RR,Sk,Ze,Kur,SNR,Sigma,w):
    
    diffZe=np.diff(Ze)


    
    for i in range(len(Type)):
##        vwaterR=2.65*np.power(Ze_1[i],.114)#values a,b from Atlas et al. 1973
##        vsnowR=.817*np.power(Ze_1[i],.063)#values a,b from Atlas et al. 1973
        hact=i*Deltah
        if ~np.isnan(BB_top) and hact>BB_top:#the BB top exists ans the type is water, so its converts to mixed or graupel
            if Type[i]==10:
                if Sk[i]>=-0.5 and w[i]>2.:
                    Type[i]=-15.
                else:
                    Type[i]=-10.
                NW[i]=np.nan;DM[i]=np.nan;LWC[i]=np.nan;RR[i]=np.nan
        if ~np.isnan(BB_bot) and hact<BB_bot:#the BB bot exists ans the type is snow, so its converts to liquid or Drizzle or graupel
            if Type[i]==-10:
                if i<np.size(diffZe[i]):

                    if Sk[i]<=-0.5 and diffZe[i]>1.:
                        Type[i]=5.
                    else:
                        
                        if abs(w[i])<= 2:#limit the fall from snow is possible found snow below BBbottom if it's lower height
                            Type[i]=-10.
                        else:
                            if Sk[i]>=-0.5 and w[i]>2.:
                                Type[i]=-15.
                            else:
                                Type[i]=10.

        if np.isnan(BB_bot):#condition that not exit bottom BB

            if Type[i]==0:
                if abs(w[i])<= 2:#limit the fall from snow
                    Type[i]=-10.
                else:
                    Type[i]=10.
                if i<np.size(diffZe):    
                    if Sk[i]<=-0.5 and diffZe[i]>1.:
                        Type[i]=5.
    
                if Sk[i]>=-0.5 and w[i]>2.:
                    Type[i]=-15.
                if Sigma[i]>1:
                    Type[i]=0
                
                
                
                
            
    return Type,NW,DM,LWC,RR
                

def Vel_Diam(v,h):
    Deltav=1+3.68*np.power(10.,-5.)*h+1.71*np.power(10.,-9.)*np.power(h,2.)
    T0=288.15#K
    L=-6.5*0.001#K/m
    R=287.053#J/kg K
    g=9.80665#m s-2
    P0=1013.25#hPa

    coe1=-L*R/g

    P=P0*np.power(1+(h*L/T0),1/coe1)

    CorrP=np.power(1000./P,0.55)

    Dgun=(-1./0.6)*np.log((1/10.3)*(9.65-(v/Deltav)))#in mm
    Dgrau=10.*np.power(v/(CorrP*6.35),1/0.87)#in mm H18 corregium
    Dhail=10.*np.power(v/(CorrP*7.6),1/0.89)#in mm H18 corregium
    return Dgun,Dgrau,Dhail
    
    


def BB(v,Z,h):#the input are fall speed, equivalent reflectivity and height
    Nonan=np.count_nonzero(~np.isnan(v))#condition for calculate the BB

    #find the BB bottom
    gv=np.diff(v)
    if np.isnan(gv).all() or Nonan<5:
        hBBbottom=np.nan;hBBtop=np.nan
    else:
        ########    USE A ANALISYS FOR CHECK IF THE BB EXIST
        ########    Cha, J. 2009: Comparison  of  the  Bright  Band Characteristics  Measured  by  MicroRain Radar (MRR) at a Mountain and a Coastal Site in SouthKorea.
        gZ=np.gradient(Z)
        Htop=h[np.argmin(gZ)]
        Hbot=h[np.argmax(gZ)]
        Hpeak=np.nan
        for j in range(len(Z)-1):
            if gZ[j]>0 and gZ[j+1]<0:
                Hpeak=h[j]
                break
        if Hbot<Hpeak and Hpeak<Htop:#condition of BB exists
####            start the method from https://doi.org/10.1007/s00376-017-7005-6
            hBBbottom=np.nan
            for i in range(len(gv)-1):
                if gv[i+1]<gv[i]:
                    hBBbottom=h[i+1]#choose the minimum because the speed to down is positive
                    indbot=i+1
                    break
                

            
            if np.isnan(hBBbottom):
                indbot=0
            dZ=np.diff(Z)
            nZ=dZ[indbot:-1]

            if nZ.size==0:
                hBBtop=np.nan
            else:
                hBBtop=np.nan
                for i in range(len(nZ)-1):
                    if nZ[i+1]>nZ[i]:
                        hBBtop=h[i+indbot+1]
                        break
        else:
            hBBbottom=np.nan;hBBtop=np.nan
            
                

    return hBBbottom,hBBtop
    
        



def Promig(vector):
    spectra=np.asarray(vector,dtype=float)
    if spectra.size==0:
        return np.ones((31,64),dtype=float)*np.nan

    no_nul=np.count_nonzero(spectra,axis=0)
    sums=np.sum(spectra,axis=0)
    out=np.full(sums.shape,np.nan,dtype=float)
    valid=no_nul>len(spectra)/(100./Ocurrence)
    np.divide(sums,no_nul,out=out,where=valid)
    return out


def group(a,indexcentral,Nnan,d):
    
    d=np.asarray(d)
    a=np.asarray(a)
    b=np.where(a>=0)
    acut=np.asarray(a[64:128])
    bcut=np.where(acut>=0)
    

    c=b[0]
    ccut=bcut[0]

    if indexcentral<=80 or indexcentral>=112:

        for i in range(np.size(b)-1):
            if c[i]-indexcentral<=0 and c[i+1]-indexcentral>=0:
                index=c[i+1]
                break
            else:
                index=indexcentral
        
        cond=1
        cont=0
        incr1=0#starts at 0

        while cond:
            if cont>=Nnan or index+incr1>=len(a)-1:
                cond=0
            
            if np.isnan(a[index+incr1]):
                cont+=1
            else:
                cont=0


            incr1+=1

        cont=0;
        incr2=1#starts at 1
        
        cond=1
        while cond:
            if cont>=Nnan or index-incr2<=0:
                cond=0
            
            if np.isnan(a[index-incr2]):
                cont+=1
            
            else:
                cont=0


            incr2+=1
        vf2=np.copy(a);xf2=np.copy(d)
        vf2[0:index-incr2+1]=np.nan
        vf2[index+incr1:]=np.nan
        xf2[0:index-incr2+1]=np.nan
        xf2[index+incr1:]=np.nan
            

    else:
        
        for i in range(np.size(bcut)-1):
            if ccut[i]-indexcentral<=0 and ccut[i+1]-indexcentral>=0:
                index=ccut[i+1]
                break
            else:
                index=indexcentral-64
        
        cond=1
        cont=0
        incr1=0#starts at 0
    
        while cond:
            if cont>=Nnan or index+incr1>=len(acut)-1:
                cond=0
            
            if np.isnan(acut[index+incr1]):
                cont+=1
            else:
                cont=0


            incr1+=1

        cont=0;
        incr2=1#starts at 1
        
        cond=1
        while cond:
            if cont>=Nnan or index-incr2<=0:
                cond=0
            
            if np.isnan(acut[index-incr2]):
                cont+=1
            
            else:
                cont=0


            incr2+=1
        blanckv=np.nan*np.ones(shape=(len(acut)))
        vf1=np.copy(acut);xf1=np.copy(d[64:128])
        vf1[0:index-incr2+1]=np.nan
        vf1[index+incr1:]=np.nan
        vff1=np.concatenate((blanckv,vf1))
        vf2=np.concatenate((vff1,blanckv))
                               
        xf1[0:index-incr2+1]=np.nan
        xf1[index+incr1:]=np.nan
        xff1=np.concatenate((blanckv,xf1))
        xf2=np.concatenate((xff1,blanckv))
        


    return vf2,xf2
    
    



def Process(matrix,he,temps,D):#This is the core from the preocessing
    neta,etan,etaNdb=HildrenS(matrix)
    Cfact=1#value from cover factor, is the number multiplicate to sigma.
    
    Etan=FindRealPeaks(etan)
    etaN=np.multiply(Etan,Cte)
    etaV=etaN/Deltav#convert eta(n) in eta(v)
    state=[]#get the values 10 to water,-10 to snow and 0 if it is impossible to
    
    zewater=[];Ni=[];VT=[];Z=[];Z_da=[];Vhail=[]
    Noise=np.multiply(neta,Cte)
    
    for m in range(len(etaV)): 
        
        proba=np.where(~np.isnan(etaN[m]))
        leN=len(etaN[m])
                ##                DELETE THE SPORADIC VALUES IN THE LAST HEIGTHS
        if len(proba[0])!=0 and m==30:
            tes1=np.where(~np.isnan(etaN[m-1]))
            tes2=np.where(~np.isnan(etaN[m-2]))
                    
            if len(tes1[0])==0 or len(tes2[0])==0:
                etaV[m]=np.ones(shape=(leN))*np.nan
                etaN[m]=np.ones(shape=(leN))*np.nan
        

        zewater.append(10**18*lamb**4*np.nansum(etaV[m])*Deltav/K2w)#Calculate by its definition of equivalent reflectivy
        nde=[];vt=[];velHail=[]
        for n in range(len(etaV[0])):#Calculate the Ze from every gate without PIA                    
            value=6.18*etaV[m][n]*dv[m]*e**(-1*0.6*D[m][n])
            
            value3=(9.65-10.3*e**(-1*0.6*D[m][n]))*dv[m]

            velHail.append(13.96*np.sqrt(10*D[m][n]))#vel from Hail Ulbrich and atlas 1982
            
            sbk=SigmaScatt[m][n]
            
            value2=(10**6)*(value/sbk)#N in m-3 mm-1
            
            nde.append(value2)#units mm-1 m-3
            
            vt.append(value3)#terminal speed in function heigh and diameter
        Vhail.append(velHail)    
        VT.append(vt)    
        Ni.append(nde)
        
        
    z,lwc,rr,ze=Parameters(Ni,D,VT,0)
    
    #stratiform case (M-P)
    vwaterR=2.65*np.power(zewater,.114)#values a,b from Atlas et al. 1973
    vsnowR=.817*np.power(zewater,.063)#values a,b from Atlas et al. 1973
    vwaterMiestr=2.65*np.power(ze,.114)
    #Thunderstorm Rain (S-S)
    
    vwaterMieconv=4.13*np.power(ze,.062)

    vwaterMie=np.nanmean([vwaterMieconv,vwaterMiestr],axis=0)
    
    speeddeal=np.arange(-64*fNy,2*64*fNy,fNy)
    NewM=[];state=[];mov=[];VerTur=[]
    W=[];Sig=[];Sk=[];lwc=[];rr=[];Z_da=[];SnowRate=[];N_da=[];Snr=[];Kurt=[];dm=[];nw=[]
    if np.sum(np.nanmean([vwaterR,vsnowR],axis=0))!=0:
        
        limitValueDeal=4#Limit value to activate the dealiasing
        DealMatrix=[]
        
        for o in range(len(etan)): 
            Snr.append(10*np.log10(1+((np.nanmax(etan[o])/neta[o]))))
                
            if o==0 or o==len(etan)-1:
                if o==0:
                    N_deal=np.ones(shape=(len(etaN[o])))*np.nan
                    n1=np.concatenate((N_deal,etaN[o]),axis=None)
                    etaN_da=np.concatenate((n1,etaN[o+1]),axis=None)
                if o==len(etan)-1:
                    N_deal=np.ones(shape=(len(etaN[o])))*np.nan
                    n1=np.concatenate((etaN[o],N_deal),axis=None)
                    etaN_da=np.concatenate((etaN[o-1],n1),axis=None)
                        
            else:
                N_deal=etaN[o-1]
                n1=np.concatenate((N_deal,etaN[o]),axis=None)
                etaN_da=np.concatenate((n1,etaN[o+1]),axis=None)

            DealMatrix.append(etaN_da) 

    ##            LOOP TO THE PRECIPITATION TYPE ESTIMATION
            Indvel=speeddeal*(etaN_da/etaN_da)
                
            
            av=np.where(etaN_da>=0.)
            av2=np.where(etaN[o]>=0.)

            
            if np.size(av)==0 or np.size(av2)==0 or np.size(av2)==64:
                
                ReVect=etaN_da*np.nan
                INewV=Indvel*np.nan
            else:
                I=np.nanargmax(np.asarray(etaN[o]))+64
                

                ReVect,INewV=group(etaN_da,I,5,Indvel)#function to find the group of values




            if np.isnan(ReVect).all():
                S=np.nan
                L=np.nan
                sigma3=np.nan
            else:
                if INewV[np.nanargmax(ReVect)]<0:
                    S=.5
                    L=5.

                else:
                                        
                    PT3=np.nansum(ReVect)
                    w3=np.nansum(np.prod([ReVect,speeddeal],axis=0))/PT3#estimated velocity
                    sigma3=np.sqrt(np.nansum(np.prod([ReVect,np.power(speeddeal-w3,2)],axis=0))/PT3)# spectral witdh
                    
                    S=(INewV[np.nanargmax(ReVect)]-vsnowR[o])
                    L=(INewV[np.nanargmax(ReVect)]-vwaterMie[o])
                    comment='nothing'
                    

            

                

            if abs(S)<=(Cfact*abs(sigma3)) and abs(L)>(Cfact*abs(sigma3)):#case not liquid, possible snow

                state.append(-10)
                if np.nanmin(INewV)<0 or np.nanmax(INewV)>12:
                    if np.nanmin(INewV)<0:
                        mov.append(-1)
                    else:
                        mov.append(1)
                else:
                    mov.append(np.nan)
                    
            if abs(S)>(Cfact*abs(sigma3)) and abs(L)<=(Cfact*abs(sigma3)):#case liquid

                state.append(10)
                if np.nanmin(INewV)<0 or np.nanmax(INewV)>12:
                    if np.nanmin(INewV)<0:
                        mov.append(-1)
                    else:
                        mov.append(1)
                else:
                    mov.append(np.nan)
            if np.isnan(L) and np.isnan(S):
                state.append(np.nan)
                if np.nanmin(INewV)<0 or np.nanmax(INewV)>12:
                    if np.nanmin(INewV)<0:
                        mov.append(-1)
                    else:
                        mov.append(1)
                else:
                    mov.append(np.nan)
            if abs(S)==abs(L) or (abs(L)<=(Cfact*abs(sigma3)) and abs(S)<=(Cfact*abs(sigma3))):#case mixed
                if INewV[np.nanargmax(ReVect)]<vwaterMie[o] and INewV[np.nanargmax(ReVect)]> vsnowR[o]:
                    state.append(0)#cas mixed
                else:
                    if INewV[np.nanargmax(ReVect)]< vsnowR[o]:
                        state.append(-10)#cas snow
                    if INewV[np.nanargmax(ReVect)]> vwaterMie[o]:
                        state.append(10)#cas rain
                        
                    
                if np.nanmin(INewV)<0 or np.nanmax(INewV)>12:
                    if np.nanmin(INewV)<0:
                        mov.append(-1)
                    else:
                        mov.append(1)
                else:
                    mov.append(np.nan)

            if np.isnan(S) and ~np.isnan(L):#case liquid, but possible wrong election
                state.append(10)
                if abs(L)>=limitValueDeal:
                    
                    LonCut=int(len(etaN[o]))
                    n1=np.ones(shape=(LonCut))*np.nan
                    n2=etaN_da[LonCut:LonCut*2]
                    nc1=np.concatenate((n1,n2))
                    ReVect=np.concatenate((nc1,n1))#vector corrected
                    mov.append(1)
                else:
                    mov.append(np.nan)
                    

                
            if ~np.isnan(S) and np.isnan(L):#case not liquid, but possible wrong election
                state.append(-10)

                if S>=limitValueDeal:
                    
                    LonCut=int(len(etaN[o])/2)
                    n1=np.ones(shape=(LonCut))*np.nan
                    n3=np.ones(3*LonCut)*np.nan
                    n2=etaN_da[LonCut:LonCut+len(etaN[o])]
                    nc1=np.concatenate((n1,n2))
                    ReVect=np.concatenate((nc1,n3))#vector corrected
                    mov.append(-1)
                else:
                    mov.append(np.nan)

                
                
                    

            if abs(L)>(Cfact*abs(sigma3)) and abs(S)>(Cfact*abs(sigma3)):#difficult case

                if abs(L)>=limitValueDeal and abs(S)>=limitValueDeal:#wrong election
                    if L-limitValueDeal<=0 or S-limitValueDeal<=0:#v expected is bigger than the found. Shift the vector from 128-32 to 128+32

                        if np.isnan(etaN_da[96:160]).all():
                            ReVect=np.ones(shape=(len(etaN_da)))*np.nan
                        else:
                            I=np.nanargmax(np.asarray(etaN_da[96:160]))+96
                            ReVect,INewV=group(etaN_da,I,5,Indvel)

                        
                        if np.isnan(ReVect).all():
                            S1=np.nan
                            L1=np.nan
                            mov.append(np.nan)
                        else:
                            mov.append(1)
                            S1=(INewV[np.nanargmax(ReVect)]-vsnowR[o])
                            L1=(INewV[np.nanargmax(ReVect)]-vwaterMie[o])
                            PT4=np.nansum(ReVect)
                            w4=np.nansum(np.prod([ReVect,speeddeal],axis=0))/PT4#estimated velocity
                            sigma4=np.sqrt(np.nansum(np.prod([ReVect,np.power(speeddeal-w4,2)],axis=0))/PT4)# spectral witdh
                        
                            
                            if (abs(L1)<=(Cfact*abs(sigma4)) and abs(S1)>(Cfact*abs(sigma4))):
                                state.append(10)
                            if ~np.isnan(S1) and abs(L1)>(Cfact*abs(sigma4)):
                                state.append(-10)
                            if abs(S1)<=(Cfact*abs(sigma4)) and abs(L1)<=(Cfact*abs(sigma4)):
                                state.append(0)
                            

                            if np.isnan(S1) and ~np.isnan(L1):
                                state.append(10)#liquid
                            if np.isnan(L1) and ~np.isnan(S1):
                                state.append(-10)#not liquid

                        if np.isnan(S1) and np.isnan(L1):
                            state.append(np.nan)
                            
                    if L-limitValueDeal>0 or S-limitValueDeal>0:#v expected is lower than the found. Shift the vector from 64-32 to 64+32




                        if np.isnan(etaN_da[32:96]).all():
                            ReVect=np.ones(shape=(len(etaN_da)))*np.nan
                        else:
                            I=np.nanargmax(np.asarray(etaN_da[32:96]))+32
                            ReVect,INewV=group(etaN_da,I,5,Indvel)

                            
                        if np.isnan(ReVect).all():
                            S1=np.nan
                            L1=np.nan
                            mov.append(np.nan)
                        else:
                            mov.append(-1)
                            S1=(INewV[np.nanargmax(ReVect)]-vsnowR[o])
                            L1=(INewV[np.nanargmax(ReVect)]-vwaterMie[o])
                            PT5=np.nansum(ReVect)
                            w5=np.nansum(np.prod([ReVect,speeddeal],axis=0))/PT5#estimated velocity
                            sigma5=np.sqrt(np.nansum(np.prod([ReVect,np.power(speeddeal-w5,2)],axis=0))/PT5)# spectral witdh
                        

                            if (abs(L1)<=(Cfact*abs(sigma5)) and abs(S1)>(Cfact*abs(sigma5))):
                                state.append(10)
                            if ~np.isnan(S1) and abs(L1)>(Cfact*abs(sigma5)):
                                state.append(-10)
                            if abs(S1)<=(Cfact*abs(sigma5)) and abs(L1)<=(Cfact*abs(sigma5)):
                                state.append(0)
                            

                            if np.isnan(S1) and ~np.isnan(L1):
                                state.append(10)#liquid
                            if np.isnan(L1) and ~np.isnan(S1):
                                state.append(-10)#not liquid

                        if np.isnan(S1) and np.isnan(L1):
                            state.append(np.nan)
                if (abs(L)-limitValueDeal<0) and (abs(S)-limitValueDeal<0):
                    if abs(S)>abs(L):
                        state.append(10)
                        mov.append(np.nan)
                    if abs(S)<abs(L):
                        state.append(-10)
                        mov.append(np.nan)
                    if abs(S)==abs(L):
                        state.append(0)
                        mov.append(np.nan)
                if (abs(L)-limitValueDeal<=0) and (abs(S)>limitValueDeal):
                    
                    state.append(10)
                    mov.append(np.nan)
                if (abs(S)-limitValueDeal<=0) and (abs(L)>limitValueDeal):
                    
                    state.append(-10)
                    mov.append(np.nan)
                    
                        
                    
            NewM.append(ReVect)
        

        valuemax=[]
        for m in range(len(NewM)): 
               

            iden=np.where(NewM[m]>=0.)
    
            if np.size(iden)==0:
                valuemax.append(np.nan)
            else:
                valuemax.append(speeddeal[np.nanargmax(NewM[m])])
     

        Dife=np.diff(valuemax)
        
        indole=np.argwhere(abs(np.diff(valuemax))>8.)
        Inindole=np.copy(indole)

            
        CountIndole=[]
        if len(indole)!=0:
            CountIndole.append(int(indole[0]))
        while len(indole)!=0:
                
            Vector=DealMatrix[int(indole[0]+1)]

            indx=np.nanargmax(NewM[int(indole[0]+1)])

                
            Indvel=speeddeal*(Vector/Vector)
                
            if Dife[int(indole[0])]>0:
                if indx>(64+32):
                    IDX=indx-64
                else:
                    IDX=indx
                CoVector,daig=group(Vector,IDX,5,Indvel)#function to find the group of values
                NewM[int(indole[0]+1)]=CoVector
                    
            else:
                if indx<(64+32):
                    IDX=indx+32
                else:
                    IDX=indx+64
                CoVector,daig=group(Vector,IDX,5,Indvel)#function to find the group of values
                NewM[int(indole[0]+1)]=CoVector
            newZe=10**18*lamb**4*np.nansum(CoVector)*Deltav/K2w
            NvwaterR=2.65*np.power(newZe,.114)#values a,b from Atlas et al. 1973
            NvsnowR=.817*np.power(newZe,.063)#values a,b from Atlas et al. 1973
            if np.isnan(CoVector).all():
                S=np.nan
                L=np.nan
            else:
                S=(speeddeal[np.nanargmax(CoVector)]-NvsnowR)
                L=(speeddeal[np.nanargmax(CoVector)]-NvwaterR)
                PT2=np.nansum(CoVector)
                w2=np.nansum(np.prod([CoVector,speeddeal],axis=0))/PT2#estimated velocity
                sigma2=np.sqrt(np.nansum(np.prod([CoVector,np.power(speeddeal-w2,2)],axis=0))/PT2)# spectral witdh

                
                if abs(L)<=(abs(sigma2)) and abs(S)>(abs(sigma2)):
                    state[int(indole[0]+1)]=10.
                if abs(S)<=(abs(sigma2)) and abs(L)>(abs(sigma2)):
                    state[int(indole[0]+1)]=-10.
                    comment='snow'
                if abs(L)>(abs(sigma2))and abs(S)>(abs(sigma2)):
                    state[int(indole[0]+1)]=20.
                    comment='unkown'
                if abs(L)<=(abs(sigma2)) and abs(S)<=(abs(sigma2)):
                    if w2>NvsnowR and w2<NvwaterR:
                        state[int(indole[0]+1)]=0.
                        comment='mixed'
                    else:
                        if w2<NvsnowR:
                            state[int(indole[0]+1)]=-10.
                            comment='snow'
                        if w2 > NvwaterR:
                            state[int(indole[0]+1)]=+10.
                            comment='rain'
                        

            valuemax=[]
            for m in range(len(NewM)): 
                   
   
                iden=np.where(NewM[m]>=0.)
   
                if np.size(iden)==0:
                    valuemax.append(np.nan)
                else:
                    valuemax.append(speeddeal[np.nanargmax(NewM[m])])
                    

                
            indole=np.argwhere(abs(np.diff(valuemax))>8.)
            Dife=np.diff(valuemax)
            if len(indole)!=0:

                if int(indole[0])==CountIndole[-1]:
                    indole=[]
                else:
                    CountIndole.append(int(indole[0]))
        

        for m in range(len(state)):#delete sporadic values
            if m!=0 and m!=len(state)-1:
                s1=state[m-1]
                s2=state[m]
                s3=state[m+1]
                if s2==0 and s1==-10 and s3==-10:
                    state[m]=-10
                if s2==0 and s1==10 and s3==10:
                    state[m]=10
                if s2==20 and s1==10 and s3==10:
                    state[m]=10
                if s2==20 and s1==-10 and s3==-10:
                    state[m]=-10
        Mwater=[]
        Msnow=[]
        Mmixed=[]
        Mhail=[]
        MDriz=[]
        Munk=[]
        ZE=[]
        Mgrau=[]
        roW=10**6 #water density g/m3

        vel=np.copy(speeddeal)
        Nde=[]
        PIA=[]
        PIA_total=[]
        PIA_total.append(1.)
############        create the vector diff Ze to detect drizzle
        Vector=[]
        for m in range(len(NewM)):
            vector=NewM[m]
            vector2=vector[64:64*2]
            ValueZeD=(10**18*lamb**4*Deltav*np.nansum(vector2))/(np.pi**5*K2w)
            Vector.append(ValueZeD)
        Zediff=np.diff(Vector)
                      
                      
############        check the type
        
        for m in range(len(NewM)):
            
            vector=NewM[m]
            
            

            PT=np.nansum(vector)
            w=np.nansum(np.prod([vector,vel],axis=0))/PT#estimated velocity
            sigma=np.sqrt(np.nansum(np.prod([vector,np.power(vel-w,2)],axis=0))/PT)# spectral witdh
            sk=np.nansum(np.prod([vector,np.power(vel-w,3)],axis=0))/(PT*pow(sigma,3))# spectral witdh
            Kur=np.nansum(np.prod([vector,np.power(vel-w,4)],axis=0))/(PT*pow(sigma,4))# Kurtossis
            ValueZe=(10**18*lamb**4*Deltav*np.nansum(NewM[m]))/(np.pi**5*K2w)
            if ValueZe<=0 or np.isnan(ValueZe):
                ZE.append(np.nan)
            else:
                ZE.append(10*np.log10(ValueZe))
            if w==0.:
                w=np.nan

            
            W.append(w)
            
            Sig.append(sigma)
            Sk.append(sk)
            Kurt.append(Kur)
            dif=[]#diference between diameters for N
            dif2=[]#diference between diameters for Z
            nde=[]
            indexFinded=[]
            for n in range(len(D[m])):
                if n==0 or n==len(D[m])-1:
                    if n==0:
                        dif2.append(D[m][n+1]-D[m][n])
                        dif.append(D[m][n+1]-D[m][n])
                    if n==len(D[m])-1:
                        dif.append(abs(D[m][n-1]-D[m][n]))
                        dif2.append(abs(D[m][n]-D[m][n-1]))
                else:
                    dif2.append(abs((D[m][n+1]-D[m][n])))
                    dif.append(abs((D[m][n+1]-D[m][n-1]))/2.)
                    condFH=speed[n]-w
                        
                    if condFH>=0:
                        indexFinded.append(n)
                        
                
                EtaV=NewM[m][64:64*2]#interval for water choosed
                value=6.18*EtaV[n]*dv[m]*e**(-1*0.6*D[m][n])
                s=SigmaScatt[m][n]
                value2=(10**6)*(value/s)#N in m-3 mm-1
                nde.append(value2)#units mm-1 m-3
                
                
                ##                APPLY THE ATTENUATTION
            DeltaR=he[3]-he[2]
            
                        
            Np=np.multiply(nde,PIA_total[-1])#m-3 mm-1
            Pro=[]
            for k in range(len(Np)):
                pro=SigmaExt[m][k]*Np[k]*dif[k]
                
                Pro.append(pro)
               
            kp=np.nansum(Pro)*10**-6#m-1
            
            num=2.*kp*DeltaR#WHERE DeltaR is m
            N=-1.*np.multiply(Np,np.log(1-num)/num)#units mm-1 m-3
            Pro2=[]
            for k in range(len(N)):
                pro2=SigmaExt[m][k]*N[k]*dif[k]
                Pro2.append(pro2)
                
            Kr=np.nansum(Pro2)*10**-6
            pia=PIA_total[-1]*e**(-2.*Kr*DeltaR)
            if pia>=10. or num==0.:
                if num==0.:
                    pia=np.nan
                else:
                    pia=10.
    
            PIA_total.append(pia)

            
            
            
            if state[m]==10:#rain case
                
                Mwater.append(NewM[m])
                SnowRate.append(np.nan)

                dif=[]#diference between diameters for N
                dif2=[]#diference between diameters for Z
                nde=[]
                indexFinded=[]
                for n in range(len(D[m])):
                    if n==0 or n==len(D[m])-1:
                        if n==0:
                            dif2.append(D[m][n+1]-D[m][n])
                            dif.append(D[m][n+1]-D[m][n])
                        if n==len(D[m])-1:
                            dif.append(abs(D[m][n-1]-D[m][n]))
                            dif2.append(abs(D[m][n]-D[m][n-1]))
                    else:
                        dif2.append(abs((D[m][n+1]-D[m][n])))
                        dif.append(abs((D[m][n+1]-D[m][n-1]))/2.)
                        condFH=speed[n]-w
                        
                        if condFH>=0:
                            indexFinded.append(n)
                        
                
                    EtaV=NewM[m][64:64*2]#interval for water choosed
                    value=6.18*EtaV[n]*dv[m]*e**(-1*0.6*D[m][n])
                    s=SigmaScatt[m][n]
                    value2=(10**6)*(value/s)#N in m-3 mm-1
                    nde.append(value2)#units mm-1 m-3
                
                #Calculate the diameter from the mean vel found
                diaWork=D[m]
                if w<=0 or w>=11:
                    if w<=0:#cas snow
                        diamHail=1
                    if w>=11:#case hail
                        diamHail=5
                else:
                    if len(indexFinded)==0:
                        diamHail=3#case liquid
                    else:
                        
                        diamHail=diaWork[indexFinded[0]]
                

                LastN=N

                

                Nde.append(LastN)

                value=np.nansum(np.prod([np.power(D[m],6),LastN,dif2],axis=0))
                value2=np.nansum(np.prod([np.power(D[m],3),LastN,dif2],axis=0))
                value3=np.nansum(np.prod([np.power(D[m],3),LastN,dif2],axis=0)*w)
                value4=np.nansum(np.prod([np.power(D[m],4),LastN,dif2],axis=0))
                
                if np.nansum(nde)<=0.:
                    N_da.append(np.nan)
                else:
                    N_da.append(np.log10(np.nansum(LastN)))

                if diamHail>=5:#Hail case
                    
                    Mhail.append(NewM[m])
                    state[m]=-20.
                    
                else:
                    Mhail.append(NewM[m]*np.nan)
                

                if ~np.isnan(sk) :
                    

                    if m<len(Zediff):
                        if sk<=-0.5 and Zediff[m]>=1.:#New criteria from empiric values. From an artcile very interesting https://doi.org/10.1175/JTECH-D-18-0158.1

                            
                            MDriz.append(NewM[m])
                            state[m]=5.
                        else:
                            MDriz.append(NewM[m]*np.nan)
                    else:
                        MDriz.append(NewM[m]*np.nan)
                    
                else:
                    MDriz.append(NewM[m]*np.nan)
                        
                        
                        
                if value<=0. or np.isnan(value):
                    Z_da.append(np.nan)
                else:
                    Z_da.append(10*np.log10(value))
                if value2==0.:
                    lwc.append(np.nan)
                else:
                    lwc.append(roW*value2*(np.pi/6.)*(10**-9))
                if value3==0.:
                    rr.append(np.nan)
                else:
                    rr.append(value3*(np.pi/6.)*(10**-9)*1000.*3600.)
                if value4==0:
                    dm.append(np.nan)
                    nw.append(np.nan)
                else:
                    dm.append(value4/value2)
                    nw.append(np.log10(256.*(roW*value2*(np.pi/6.))/ (np.pi*roW*(value4/value2)**4)))#units m-3 mm-1
                if mov[m]==-1:#case rain and upward
                      VerTur.append((2.6*np.power(ValueZe,.107))-w)
                if mov[m]==1:#case rain and downward
                      VerTur.append(w-(2.6*np.power(ValueZe,.107)))
                if np.isnan(mov[m]):#case rain and upward
                      VerTur.append(np.nan)
               
            else:
                Mwater.append(NewM[m]*np.nan)
                
                
            if state[m]==-10:#Snow case
                
                Msnow.append(NewM[m])


                if ValueZe<=0 or np.isnan(ValueZe):
                    
                    SnowRate.append(np.nan)
                else:
                    if ~np.isnan(sk):

                        if sk>=-0.5 and w>2.:
                            state[m]=-15.
                    
                    SnowRate.append(np.power(ValueZe/56.,1/1.2))#following Matrosov (2007) constants - https://link.springer.com/article/10.1007/s00703-011-0142-z#CR15
                Z_da.append(np.nan)
                lwc.append(np.nan)
                nw.append(np.nan)
                dm.append(np.nan)
                rr.append(np.nan)
                N_da.append(np.nan)
                PIA.append(np.nan)
                Nde.append(np.ones(shape=(len(etaN[1])))*np.nan)
                if mov[m]==-1:#case snow and upward
                      VerTur.append((.817*np.power(ValueZe,.063))-w)
                if mov[m]==1:#case snow and downward
                      VerTur.append(w-(.817*np.power(ValueZe,.063)))
                if np.isnan(mov[m]):
                      VerTur.append(np.nan)
                    
                
                
            else:
                Msnow.append(NewM[m]*np.nan)
                


            if state[m]==0:#Mixed case
                if m<len(Zediff):
                    if ~np.isnan(sk):
                        if sk<=-0.5 and Zediff[m]>1.0:
                            state[m]=5.
                    
    
    ####################criteria from doi:10.5194/acp-16-2997-2016
                        if sk>=0. and w>2.:
                            state[m]=-15.
                        if sigma>0:
                            state[m]=0.
                    
                Mmixed.append(NewM[m])
                Value=10**18*lamb**4*Deltav*np.nansum(NewM[m])/(np.pi**5*K2w)
                
                Z_da.append(np.nan)
                lwc.append(np.nan)
                dm.append(np.nan)
                nw.append(np.nan)
                rr.append(np.nan)
                N_da.append(np.nan)
                PIA.append(np.nan)

                SnowRate.append(np.nan)
                Nde.append(np.ones(shape=(len(etaN[1])))*np.nan)
                if mov[m]==-1:#case mixed and upward
                      VerTur.append((.817*np.power(ValueZe,.063))-w)
                if mov[m]==1:#case mixed and downward
                      VerTur.append(w-(.817*np.power(ValueZe,.063)))
                if np.isnan(mov[m]):
                      VerTur.append(np.nan)
                            
            else:
                Mmixed.append(NewM[m]*np.nan)
                
            if np.isnan(state[m]):
                Mwater.append(NewM[m]*np.nan)
                Msnow.append(NewM[m]*np.nan)
                Mmixed.append(NewM[m]*np.nan)
                Mhail.append(NewM[m]*np.nan)
                MDriz.append(NewM[m]*np.nan)
                Munk.append(NewM[m]*np.nan)
                Mgrau.append(NewM[m]*np.nan)
                Z_da.append(np.nan)
                lwc.append(np.nan)
                nw.append(np.nan)
                dm.append(np.nan)
                rr.append(np.nan)
                N_da.append(np.nan)
                SnowRate.append(np.nan)
                Nde.append(np.ones(shape=(len(etaN[1])))*np.nan)
                VerTur.append(np.nan)
                PIA.append(np.nan)

                
            if state[m]==20:#cas unknown
                Munk.append(NewM[m])
                
                
                Value=10**18*lamb**4*Deltav*np.nansum(NewM[m])/(np.pi**5*K2w)#use the rayleight estimation
                
                Z_da.append(np.nan)
                lwc.append(np.nan)
                nw.append(np.nan)
                dm.append(np.nan)
                rr.append(np.nan)
                N_da.append(np.nan)
                PIA.append(np.nan)

                SnowRate.append(np.nan)
                Nde.append(np.ones(shape=(len(etaN[1])))*np.nan)
                if mov[m]==-1:#case hail and upward, using the same for snow
                      VerTur.append((.817*np.power(ValueZe,.063))-w)
                if mov[m]==1:#case hail and downward, using the same for snow
                      VerTur.append(w-(.817*np.power(ValueZe,.063)))
                if np.isnan(mov[m]):
                      VerTur.append(np.nan)
                            
            else:
                Munk.append(NewM[m]*np.nan)
                            
        for m in range(len(state)):
            if m!=0 and m!=len(state)-1:
                s1=state[m-1]
                s2=state[m]
                s3=state[m+1]
                if s2==-20 and s1==10 and s3==10:
                    state[m]=10        
                
                

        

    else:#There is not Signal
        
        blanck=np.nan*np.ones(shape=(len(etaN)))
        state=blanck
        NewM=(etaN*np.nan)
        Z_da=blanck
        lwc=blanck
        nw=blanck
        dm=blanck
        rr=blanck
        N_da=blanck
        W=blanck
        Sig=blanck
        Sk=blanck
        Kurt=blanck
        SnowRate=blanck
        Nde=(etaN*np.nan)
        ZE=blanck
        mov=blanck
        VerTur=blanck
        Snr=blanck
        PIA=np.nan*np.ones(shape=(len(etaN)+1))
        PIA_total=np.nan*np.ones(shape=(len(etaN)+1))
    if len(PIA)==31:
        PIA.append(np.nan)
    if len(PIA_total)==31:
        PIA_total.append(np.nan)
    return state,NewM,Z_da,lwc,rr,SnowRate,W,Sig,Sk,Noise,N_da,Nde,ZE,mov,VerTur,Snr,Kurt,PIA,nw,dm,PIA_total

       
    
def group_consecutives(vals, step=1):
    """Return list of consecutive lists of numbers from vals (number list)."""
    run = []
    result = [run]
    expect = None
    for v in vals:
        if (v == expect) or (expect is None):
            run.append(v)
        else:
            run = [v]
            result.append(run)
        expect = v + step
    return result

def Parameters(n,d,v,da):#the differences between diameter aren't constant
    Z=[];lwc=[];rr=[];ze=[]
    
    roW=10**6 #water density g/m3
    for i in range(len(n)):
        D=np.asarray(d[i],dtype=float)
        N=np.asarray(n[i],dtype=float)
        w=np.asarray(v[i],dtype=float)
        
        
        if da==1:#the code is in dealiased axes
            dif=np.empty_like(D,dtype=float)
            dif[0]=D[1]-D[0]
            dif[-1]=abs(D[-2]-D[-1])
            middle=np.arange(1,len(D)-1)
            left_half=middle < len(w)/2.
            dif[middle[left_half]]=D[middle[left_half]+1]-D[middle[left_half]]
            dif[middle[~left_half]]=np.abs(D[middle[~left_half]]-D[middle[~left_half]+1])

        else:
            dif=np.empty_like(D,dtype=float)
            dif[:-1]=D[1:]-D[:-1]
            dif[-1]=D[-1]-D[-2]
        D3=np.power(D,3)
        value=np.nansum(D3*D3*N*dif)
        value2=np.nansum(D3*N*dif)
        value3=np.nansum(D3*N*dif*w)
        if value==0.:
            Z.append(np.nan)
            ze.append(np.nan)
        else:
            Z.append(10*np.log10(value))
            ze.append(value)
        if value2==0.:
            lwc.append(np.nan)
        else:
            lwc.append(roW*value2*(np.pi/6.)*(10**-9))
        if value3==0.:
            rr.append(np.nan)
        else:
            rr.append(value3*(np.pi/6.)*(10**-9)*1000.*3600.)
        
    return Z,lwc,rr,ze

def FindRealPeaks(matrix):#function to detect real peaks, wherein a peak has a minimum 3 consecutives values
    Matrix=[]
    for i in range(len(matrix)):
        vector=np.asarray(matrix[i])
        Vector=np.ones(shape=(len(vector)))*np.nan
        valid=~np.isnan(vector)
        if valid.any():
            edges=np.diff(np.concatenate(([False],valid,[False])).astype(int))
            starts=np.flatnonzero(edges==1)
            stops=np.flatnonzero(edges==-1)
            for start,stop in zip(starts,stops):
                if stop-start>=3:
                    Vector[start:stop]=vector[start:stop]
        Matrix.append(Vector)
                    
        
                
        
    return Matrix

def ScatExt(diameter,longW):#for 1 height gate
    ag_lam=longW*1000.#mm Convert lamb from m to mm

    ag_mre=6.417
    ag_mim=2.758
    m = ag_mre + 1.0j * ag_mim
    
    scatt=[];extinct=[]
    for i in range(len(diameter)):
        r=diameter[i]/2.

        if np.isnan(r):
            scatt.append(np.nan)
            extinct.append(np.nan)

        else:
            
            x = 2*np.pi*r/ag_lam;#is non dimension, so the ag_lam and r have the same units
            qext, qsca, qback, g = mie_efficiencies(m,x)
            absorb  = (qext - qsca) * np.pi * r**2
            scatt.append(qsca * np.pi * r**2)
            extinct.append(qext* np.pi * r**2)
    return scatt,extinct#the output are mm^2
            

        




def HildrenS(matrix):
    Pot=matrix
    
    PotHS=[]
    Noise=[]
    PotWithOutHS=[]
    for j in range(len(Pot)):
        v=Pot[j]#is the spectrum bins for one height
        v2=np.ones(shape=(len(v)))*np.nan#create the vector result
        meanv=np.nanmean(v)
        varv=np.nanvar(v)
        if (meanv**2/(varv))>58 or varv==0 or np.isnan(varv):#bad signal
            v2=np.ones(shape=(len(v)))*np.nan
            soroll=np.nan
            PotWithOutHS.append(v2)
        else:
                
            indMax=Peak(v)
            maxim=indMax[np.nanargmax(v[indMax])]
        
            
            v[v>v[maxim]]=np.nan
            PotWithOutHS.append(v)
            
            condition=1
            while condition:
                meanv=np.nanmean(v)
                varv=np.nanvar(v)
                if (np.power(meanv,2)/varv)>58 or varv==0.:
                    soroll=meanv
                    condition=0

                max_index=np.nanargmax(v)
                max_value=v[max_index]
                np.put(v2,max_index,max_value)
                np.put(v,max_index,np.nan)
        v2[v2<=1.2*soroll]=np.nan#Record the signal up 1.2 the noise level found

        Noise.append(soroll)
        PotHS.append(v2-soroll)
    return Noise,PotHS,PotWithOutHS


             





def date2unix(date):
    return calendar.timegm(date.timetuple())
def unix2date(unix):
    return datetime.datetime.utcfromtimestamp(unix)

def Peak(vector):
    vector=np.asarray(vector)
    if len(vector)<3:
        return []
    return np.flatnonzero((vector[1:-1]>=vector[2:]) & (vector[1:-1]>=vector[:-2]))+1






velc=299792458.#light speed 
lamb=velc/(24.23*1e9)  #The frequency of radar is 24.23 GHz, units from lamb m
ag_lam=lamb
fsampling=125000#Hz frequencu sampling
fNy=fsampling*lamb/(2*2*32*64) 
speed=np.arange(0,64*fNy,fNy)
speed21=np.arange(0,32*fNy,fNy)
speed22=np.arange(-32*fNy,0,fNy)
speed2=np.concatenate((speed21,speed22),axis=0)
K2w=0.92
K2i=0.18
K2s=np.mean((K2w,K2i))
Deltaf=fsampling/(2*32*64) #around 30 Hz
CetNtoetaV=2./(Deltaf*lamb)
Deltav=Deltaf*lamb/2.
Ocurrence=50.#value in % of ocurrence in the averaging matrix
