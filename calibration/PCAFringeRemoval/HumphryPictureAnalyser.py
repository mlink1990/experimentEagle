# -*- coding: utf-8 -*-
"""
Created on Mon Mar 26 14:20:41 2018

@author: User
"""

import numpy as np
import os
import pandas as pd
from scipy.misc import imread
from scipy.optimize import curve_fit
import scipy.ndimage.interpolation
import matplotlib.pyplot as plt
import scipy
import random

class HumphryPictureAnalyser:
    """
Class which can take care of importing pictures and basic picture analysis. 

    Important Parameters:
        camera_string   ---     Deterimes the camera and the initial values for the region of interest, Pixel size etc
        data_path_dict  ---     Dictionary which contains arbitrary chosen names (set_name) as keys (which will be refered to in the functions)
                                as well as the eagle log names (not the full path, this is done by the __init__ function)
    """
#N:\TemporaryDataStorage\TOFAtomNumber\eagleWatchedFolder\    
    def __init__(self, data_path_dict, camera_string="ANDOR0FT", data_storage="URSA", cut_white_line=False):        
        
        if data_storage == "URSA":
            self.default_file_path=os.path.join("\\\\ursa","AQOGroupFolder","Experiment Humphry","Data", "eagleLogs")
            self.wrong_path = "G:/Experiment Humphry/Data/TOF Atom Number/eagleWatchedFolder\\" #the filepath in the csv is referenced to eagleWatchedFolder 
        elif data_storage == "HUMPHRY":
            self.default_file_path=os.path.join("\\\\Quantum54","Humphry","Data","eagleLogs")
            self.wrong_path = "N:/TemporaryDataStorage/TOFATomNumber/eagleWatchedFolder\\" #the filepath in the csv is referenced to eagleWatchedFolder 
        self.darkImagePath = os.path.join("\\\\ursa", "AQOGroupFolder", "Experiment Humphry", "Experiment Control and Software", "darkImages", "darkAverageData", "2016-10-20","2016-10-20-darkAverage.gz" )                                      
               
        
        
        self.data_path_dict = self.prepare_data_path_dict(data_path_dict) #Since the entries differ for different analysations, it has to be passed on class creation
        
        #Everything is initialised for ANDOR0FT
        if camera_string=="ANDOR0FT":
            self.CAMERA_STRING = "ANDOR0FT"
            
            #The following are centered around the atom cloud            
            self.XMIN = 350
            self.XMAX = 420
            self.YMIN = 300
            self.YMAX = 360
            
            #Full size
            self.XMIN_FULL = 0
            self.XMAX_FULL = 512
            self.YMIN_FULL = 0
            self.YMAX_FULL = 512
            
            self.PX_SIZE = 16E-6 #m
            self.MAGNIFICATION = 4.25
            self.transferToOD = True
            self.ANGLE = -47.8

            self.cut_white_line = cut_white_line # tested for ANDOR1
            
        elif camera_string=="ALTA0scaledOpticalDensity":
            self.CAMERA_STRING = "ALTA0scaledOpticalDensity"
            
            #The following are centered around the atom cloud            
            self.XMIN = 410
            self.XMAX = 629
            self.YMIN = 104
            self.YMAX = 186
            
            #Full size
            self.XMIN_FULL = 0
            self.XMAX_FULL = 512
            self.YMIN_FULL = 0
            self.YMAX_FULL = 512
            
            self.PX_SIZE = 9E-6 #m
            self.MAGNIFICATION = 1
            self.transferToOD = False
            
    def prepare_data_path_dict(self, dp_dict):
        """
        This function adds the default file path (ursa) to the dictionary with the log names.
        """
        return {x:os.path.join(self.default_file_path, y, y+".csv") for x, y in dp_dict.iteritems()}

    def get_coordinate_grid(self, ROI=None):
        if ROI is None:
            ROI = (self.XMIN, self.XMAX, self.YMIN, self.YMAX)
        (XMIN, XMAX, YMIN, YMAX) = ROI
        (xs, ys) = (np.arange(XMIN, XMAX), np.arange(YMIN, YMAX))
        xs, ys = np.meshgrid(xs, ys)
        return xs, ys
    
    def load_picture(self, set_name, camera=None, transferToOD=None, ROI=None, filename=None, \
    variable_name=None, variable_value=None):
        """
This method provides tools to look at single pictures in an eagle log. 

    Arguments:
    set_name        ---     set_name referring to key in data_path_dict
    camera          ---     camera_string, default is self.CAMERA_STRING
    transferToOD    ---     transfer to OD? default is self.transferToOD
    ROI             ---     Region of interest format and default (self.XMIN, self.XMAX, self.YMIN, self.YMAX)
    filename        ---     filename of picture, default is None, which shows a random picture from the log
    
This function simply returns a single picture from an eagle log as a 2D array. One can either choose a filename for display, 
or a random picture from the images folder will be selected.
        """
        if camera is None:
            camera = self.CAMERA_STRING
        if transferToOD is None:
            transferToOD = self.transferToOD
        if type(transferToOD) is not bool:
            transferToOD = self.transferToOD
        if ROI is None:
            ROI = (self.XMIN, self.XMAX, self.YMIN, self.YMAX)
        
        (XMIN, XMAX, YMIN, YMAX) = ROI
        
        csv_path = self.data_path_dict[set_name]
        image_path = os.path.join(self.data_path_dict[set_name].split(self.data_path_dict[set_name].split("\\")[-1])[0], "images")
        
        full_csv = pd.read_csv(csv_path).set_index("img file name")
        
        if (variable_name is not None) and (variable_value is not None):
            filenames = full_csv.groupby(variable_name).get_group(variable_value).index.values
        
        if filename is not None:
            if transferToOD is False:            
                return self.cut_to_ROI(XMIN, XMAX, YMIN, YMAX, scipy.misc.imread(os.path.join(image_path, filename)).astype(scipy.float_))[2]
            else:          
                return self.transfertoOD(scipy.misc.imread(os.path.join(image_path, filename)).astype(scipy.float_), ROI=(XMIN, XMAX, YMIN, YMAX))[2]
            
        else:
            filenames = [_.split("\\")[-1] for _ in full_csv.index.values]
            idx = random.randint(0, len(filenames)-1)
            if transferToOD is False:            
                return self.cut_to_ROI(XMIN, XMAX, YMIN, YMAX, scipy.misc.imread(os.path.join(image_path, filenames[idx])).astype(scipy.float_))[2]
            else:          
                return self.transfertoOD(scipy.misc.imread(os.path.join(image_path, filenames[idx])).astype(scipy.float_), ROI=(XMIN, XMAX, YMIN, YMAX))[2]
            
    
    
    def load_pictures(self, set_name, camera=None, transferToOD=None, average=False, average_variable=None, variable=None, ROI = None):
        """
This functionc an be used to load_pictures with a variety of options. 

    Arguments:
    set_name            ---     name of the log from self.data_path_dict
    camera              ---     camera string, can determine initial values for region of interest, OD transformation etc.
    transferToOD        ---     Should the picture be translated to OD? Default is self.transferToOD
    average             ---     Determines if averaging should be done over all pictures in the log
    average_variable    ---    Determines if averaging should be done over a certain variable in the log
    variable            ---     Determines variable for ordering / grouping pictures. Default is epoch seconds
    ROI                 ---     Region of interest. Default is self.XMIN, self.XMAX, self.YMIN, self.YMAX
    
Note: The hierarchy for ordering is average_variable > average > variable. This means if there is a average_variable given, the 
function will average over this variable and return before checking average or variable. If average is True and average_variable
is None, this function will just return the averaged picture over all single pictures. 
The return value is always a dictionary, where keys are either the values of average_variable, variable or - in the case of 
average == True "averaged_picture". The values of this dictionary are pictures or a list of pictures (in the variable-case).

Notes:
    -) OD is taken before averaging for all options
    -) This function does not return xs, ys as the coordinates. This could in principle be implemented to keep the pixel numbers
        according to the ROI. 
        """
        if camera is None:
            camera = self.CAMERA_STRING
        if transferToOD is None:
            transferToOD= self.transferToOD
        elif type(transferToOD) is not bool:
            transferToOD= self.transferToOD
        if variable is None:
            variable = "epoch seconds"
        if ROI is None:
            ROI = (self.XMIN, self.XMAX, self.YMIN, self.YMAX)
#        elif ROI is "full":
#            ROI = "full"
        else:
            (XMIN, XMAX, YMIN, YMAX) = ROI
            
        csv_path = self.data_path_dict[set_name]
        image_path = os.path.join(self.data_path_dict[set_name].split(self.data_path_dict[set_name].split("\\")[-1])[0], "images")
        
        full_csv = pd.read_csv(csv_path).set_index("img file name")
        
        if average_variable is not None:
            all_variables = list( set(full_csv[average_variable].tolist()) )

            #return all filenames for the same variable
            grouped_filenames = { str(val): full_csv[[average_variable]].groupby(average_variable).get_group(val) for val in all_variables}
            
            #Create a dictionary with variable as key and an array of filenames
            grouped_filenames_list = {str(key): val.index.values for key, val in grouped_filenames.iteritems()}
            
            #get xs, ys
#            shape = np.shape(scipy.misc.imread(os.path.join(image_path, grouped_filenames_list.values()[0].split("\\")[-1])))
#            (xs, ys) = np.meshgrid((shape[0], shape[1]))            
            
            #Now load pictures, cut to ROI and average, in a nice memory-safe way
            #Important: Take OD before averaging, cut to ROI before averaging - saves memory
            if transferToOD is False:
                grouped_averaged_pictures = {str(key): np.mean([self.cut_to_ROI(XMIN, XMAX, YMIN, YMAX, scipy.misc.imread(os.path.join(image_path, _.split("\\")[-1])).astype(scipy.float_))[2] \
                for _ in value], axis = 0) for key, value in grouped_filenames_list.iteritems()}
                
                return grouped_averaged_pictures
            
            #Do the same, but take the OD first
            if transferToOD is True:
                grouped_averaged_pictures = {str(key): np.mean([self.transfertoOD(scipy.misc.imread(os.path.join(image_path, _.split("\\")[-1])).astype(scipy.float_), ROI=(XMIN, XMAX, YMIN, YMAX))[2] \
                for _ in value], axis = 0) for key, value in grouped_filenames_list.iteritems()}
                
                return grouped_averaged_pictures
                
        #average over all pictures
        elif average is True:
            all_filepaths = [os.path.join(image_path, _.split("\\")[-1]) for _ in full_csv.index.values]
            if transferToOD is True:            
                all_pictures = [self.transfertoOD(scipy.misc.imread(_).astype(scipy.float_), ROI = (XMIN, XMAX, YMIN, YMAX))[2] for _ in all_filepaths]
            if transferToOD is False:
                all_pictures = [self.cut_to_ROI(XMIN, XMAX, YMIN, YMAX, scipy.misc.imread(_).astype(scipy.float_))[2] for _ in all_filepaths]
            return {"averaged_picture": np.mean(all_pictures, axis = 0)}
            
        #Returns all pictures sorted by variable
        else:
            #All occurences of variable
            all_variables = list( set( full_csv[variable].tolist()))
            
            #return all filenames for the same variable
            grouped_filenames = { str(val): full_csv[[variable]].groupby(variable).get_group(val) for val in all_variables}
            
            #Create a dictionary with variable as key and an array of filenames as value
            grouped_filenames_list = {str(key): val.index.values for key, val in grouped_filenames.iteritems()}
            
            #Now load pictures and cut to ROI:
            if transferToOD is False:
                grouped_pictures = {str(key): [self.cut_to_ROI(XMIN, XMAX, YMIN, YMAX, scipy.misc.imread(os.path.join(image_path, _.split("\\")[-1])).astype(scipy.float_))[2] for _ in value] \
                for key, value in grouped_filenames_list.iteritems()}
                    
                return grouped_pictures
                
            if transferToOD is True:
                grouped_pictures = {str(key): [self.transfertoOD(scipy.misc.imread(os.path.join(image_path, _.split("\\")[-1])).astype(scipy.float_), ROI=(XMIN, XMAX, YMIN, YMAX))[2] for _ in value] \
                for key, value in grouped_filenames_list.iteritems()}
                    
                return grouped_pictures

        
    def load_pictures_to_dict(self, set_name, variable=None, camera=None, transferToOD=None, average=True):
        """
        --- OBSOLETE --- USE load_pictures FUNCTION ---        
        
        This function prepares pictures for analysis.
        Takes:
        set_name        --- Name of the set in self.data_path_dict
        variable        --- If you loop over an variable, you can decide wether you want to average over it, 
                            None takes the time stamp from the filename (so it's basically epoch seconds)
        camera          --- determines camera_string and therefore properties, default is self.CAMERA_STRING
        transferToOD    --- transfer to OD? Default is self.transferToOD
        average         --- average over pictures ?
        """
        if camera is None:
            camera = self.CAMERA_STRING
        if transferToOD is None:
            transferToOD= self.transferToOD
            
        image_path = os.path.join(self.data_path_dict[set_name], "images")
        files = [os.path.join(image_path, _) for _ in os.listdir(image_path)]
        if variable is not None:    
            variables = [_.split(variable+"_")[1].split('_')[0] for _ in os.listdir(image_path)]    
            pictures_dict = {x:imread(y) for x, y in zip(variables, files)}
            return pictures_dict
        else:
            times = [_.split(camera+"_")[1] for _ in os.listdir(image_path)]
            pictures_dict = {x:imread(y) for x, y in zip(times, files)}
            if average == True:
                averaged_picture = self.average_pictures(pictures_dict)
                if transferToOD==True:
                    averaged_picture = self.transfertoOD(averaged_picture.astype(scipy.float_))[2]
                return averaged_picture
            else:
                (xs, ys) = scipy.meshgrid(np.arange(np.shape(pictures_dict.values()[0])[0]), np.arange(np.shape(pictures_dict.values()[0])[1]))
                if transferToOD == True:            
                    pictures_dict = {x:self.transfertoOD(self.get_subSpaceArrays(xs, ys, y, self.XMIN, self.YMIN, self.XMAX, self.YMAX)[2]) for x, y in pictures_dict.iteritems()}
                else:
                    pictures_dict = {x:self.get_subSpaceArrays(xs, ys, y, self.XMIN, self.YMIN, self.XMAX, self.YMAX)[2] for x, y in pictures_dict.iteritems()}
                return pictures_dict

    def get_subSpaceArrays(self, xs, ys, zs, startX, startY, endX, endY):
        """returns the arrays of the selected sub space. If subspace is not
        activated then returns the full arrays"""
        xs = xs[startY:endY,startX:endX]
        ys = ys[startY:endY,startX:endX]
        zs = zs[startY:endY,startX:endX]                        
        return xs,ys,zs
        
    def opticalDensity(self, atomArray, lightArray):
        if atomArray.shape != lightArray.shape:
            return None
        if (not scipy.all(atomArray>=0.0)) or (not scipy.all(lightArray>0.0)):
            atomArray = atomArray.clip(1)
            lightArray = lightArray.clip(1)
        return -scipy.log(atomArray/lightArray)
    
    def rotate(self, array, angle):
        """bilinear interpolation used and standard scipy rotation """
        return scipy.ndimage.interpolation.rotate(array, angle, order=1)
    
    def fastKineticsCrop(self, rawArray,n):
        """in fast kinetic picture we have one large array and then need to crop it into n equal arrays vertically.
        Uses scipy split function which returns a python list of the arrays
        returned list has the order of first picture taken --> last picture taken. i.e. [atomsImage,lightImage]"""
        if self.cut_white_line:
            # split the image, but remove some lines, which are usually very bright, we are not quite sure about the reason
            cut1 = 509
            padding = 3
            pic1, pic2 = rawArray[:cut1], rawArray[cut1+padding:2*cut1+padding]
            return pic1, pic2
        else:
            try:
                return scipy.split(rawArray, n, axis=0)
            except ValueError as e:
                print "Kinetics crop did not work"
    
    def loadDarkImage(self, darkFilePath):
        """ dark images should be saved using scipy.savetxt(.gz, array)"""
        return scipy.loadtxt(darkFilePath)
        
    def transfertoOD(self, pic, angle = None, ROI = None, ROI_rotated = True):
        """
        Takes an Andor picture (taken in kinetics mode), crops it, subtracts dark picture
        and transfers it so optical density. Also returns coordinates, as it cuts the picture 
        to a region of interest.
        """
        
        if angle == None:
            angle = self.ANGLE
            
        (XMIN, XMAX, YMIN, YMAX) = ROI
        
        #Dark Image subtraction
        darkArray = self.loadDarkImage(self.darkImagePath)
        pic -= darkArray
        pic=pic.clip(1)
                
        #Image processing
        [atomsArray, lightArray] = self.fastKineticsCrop(pic, 2)
        ODArray = self.opticalDensity(atomsArray, lightArray)
        ODArray = self.rotate(ODArray, angle)
        n, m = np.shape(ODArray)        
        
        #Rotation might change the size of the picture        
        self.YMIN_FULL = 0
        self.YMAX_FULL = n
        self.XMIN_FULL = 0
        self.XMAX_FULL = m
        
        if ROI == None:
            ROI = (self.XMIN, self.XMAX, self.YMIN, self.YMAX)
        elif ROI is "full":
            ROI = (self.XMIN, self.XMAX, self.YMIN, self.YMAX)
        
        (xs, ys) = scipy.meshgrid(np.arange(np.shape(ODArray)[0]), np.arange(np.shape(ODArray)[1]))
        xs, ys, ODArray = self.get_subSpaceArrays(xs, ys, ODArray, XMIN, YMIN, XMAX, YMAX) #200, 200, 512, 512 = xmin, ymin, xmax, ymax
        
        return xs, ys, ODArray
    
    def cut_to_ROI(self, XMIN, XMAX, YMIN, YMAX, pic):
        (xs, ys) = scipy.meshgrid(np.arange(np.shape(pic)[0]), np.arange(np.shape(pic)[1]))
        xs, ys, pic = self.get_subSpaceArrays(xs, ys, pic, XMIN, YMIN, XMAX, YMAX)
        return xs, ys, pic
        
    def get_ROI_Dimension(self):
        return (self.YMAX-self.YMIN, self.XMAX-self.XMIN)
    
    #def get_pictureDimension(self)
    
    def set_maximum_ROI(self):
        self.XMIN = self.XMIN_FULL
        self.XMAX = self.XMAX_FULL
        self.YMIN = self.YMIN_FULL
        self.YMAX = self.YMAX_FULL
        
    def average_pictures(self, pictures_dict):
        pictures_array = [value for value in pictures_dict.values()]
        return np.mean(pictures_array, axis = 0)
        
if __name__ == "__main__":
    data_path_dict = {"2018_03_20_stab": "2018 03 20 - tem01 stability log", 
                  "2018_03_26_stab": "2018 03 26 - tem01 stability",}
    
    humphry_andor = HumphryPictureAnalyser(data_path_dict)
    humphry_alta = HumphryPictureAnalyser(data_path_dict, camera_string="ALTA0scaledOpticalDensity")
