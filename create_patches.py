# internal imports
from wsi_core.WholeSlideImage import WholeSlideImage, StitchPatches

# other imports
import os
import numpy as np
import time
import argparse
import pdb
import pandas as pd

def stitching(file_path, downscale = 64):
	start = time.time()
	heatmap = StitchPatches(file_path, downscale=downscale, bg_color=(0,0,0), alpha=-1, draw_grid=False)
	total_time = time.time() - start
	
	return heatmap, total_time

####********************************************************************
#Modified by Qinghe 23/04/2021
#def segment(WSI_object, seg_params, filter_params):
def segment(WSI_object, seg_params, filter_params, annotations, annotation_dir, slide):
 ####********************************************************************
	### Start Seg Timer
	start_time = time.time()

	# Segment
    ###*********************************
    ### Modified by Qinghe 23/04/2021
#    WSI_object.segmentTissue(**seg_params, filter_params=filter_params)
	WSI_object.segmentTissue(**seg_params, filter_params=filter_params, annotations=annotations, annotation_dir=annotation_dir, 
                          slide_name=slide)
    ###*********************************

	### Stop Seg Timers
	seg_time_elapsed = time.time() - start_time   
	return WSI_object, seg_time_elapsed

####********************************************************************
#Modified by Qinghe 23/04/2021
#def patching(WSI_object, **kwargs):
def patching(WSI_object, annotations, **kwargs):
####********************************************************************
    
	### Start Patch Timer
	start_time = time.time()

	# Patch
    ####********************************************************************
    #Modified by Qinghe 23/04/2021
    #file_path = WSI_object.createPatches_bag_hdf5(**kwargs, save_coord=True)
	file_path = WSI_object.createPatches_bag_hdf5(**kwargs, save_coord=True, annotations=annotations)
    ####********************************************************************

	### Stop Patch Timer
	patch_time_elapsed = time.time() - start_time
	return file_path, patch_time_elapsed

def initialize_df(slides, seg_params, filter_params, vis_params, patch_params):
	total = len(slides)
	df = pd.DataFrame({'slide_id': slides, 'process': np.full((total), 1, dtype=np.uint8), 
		'status': np.full((total), 'tbp'),
		
		# seg params
		'seg_level': np.full((total), int(seg_params['seg_level']), dtype=np.int8),
		'sthresh': np.full((total), int(seg_params['sthresh']), dtype=np.uint8),
		'mthresh': np.full((total), int(seg_params['mthresh']), dtype=np.uint8),
		'close': np.full((total), int(seg_params['close']), dtype=np.uint32),
		'use_otsu': np.full((total), bool(seg_params['use_otsu']), dtype=bool),
		
		# filter params
		'a_t': np.full((total), int(filter_params['a_t']), dtype=np.uint32),
		'a_h': np.full((total), int(filter_params['a_h']), dtype=np.uint32),
		'max_n_holes': np.full((total), int(filter_params['max_n_holes']), dtype=np.uint32),

		# vis params
		'vis_level': np.full((total), int(vis_params['vis_level']), dtype=np.int8),
		'line_thickness': np.full((total), int(vis_params['line_thickness']), dtype=np.uint32),

		# patching params
		'white_thresh': np.full((total), int(patch_params['white_thresh']), dtype=np.uint8),
		'black_thresh': np.full((total), int(patch_params['black_thresh']), dtype=np.uint8),
		'use_padding': np.full((total), bool(patch_params['use_padding']), dtype=bool),
		'contour_fn': np.full((total), patch_params['contour_fn'])
		})
	return df

####********************************************************************
#Modified by Qinghe 23/04/2021
#def seg_and_patch(source, save_dir, patch_save_dir, mask_save_dir, stitch_save_dir, 
def seg_and_patch(source, save_dir, patch_save_dir, mask_save_dir, stitch_save_dir, annotation_dir, 
####********************************************************************
				  patch_size = 256, step_size = 256, custom_downsample=1, 
				  seg_params = {'seg_level': -1, 'sthresh': 8, 'mthresh': 7, 'close': 4, 'use_otsu': False},
				  filter_params = {'a_t':100, 'a_h': 16, 'max_n_holes':10}, 
				  vis_params = {'vis_level': -1, 'line_thickness': 500},
				  patch_params = {'white_thresh': 5, 'black_thresh': 40, 'use_padding': True, 'contour_fn': 'four_pt'},
				  patch_level = 0,
				  use_default_params = False, 
				  seg = False, save_mask = True, 
				  stitch= False, 
                  ####********************************************************************
                  #Modified by Qinghe 23/04/2021
#				  patch = False, auto_skip=True, process_list = None):
				  patch = False, auto_skip=True, process_list = None, annotations=False):
                  ####********************************************************************

	slides = sorted(os.listdir(source))
	slides = [slide for slide in slides if os.path.isfile(os.path.join(source, slide))]
	if process_list is None:
		df = initialize_df(slides, seg_params, filter_params, vis_params, patch_params)
	
	else:
		df = pd.read_csv(process_list)

	mask = df['process'] == 1
	process_stack = df[mask]

	total = len(process_stack)
	seg_times = 0.
	patch_times = 0.
	stitch_times = 0.

	for i in range(total):
		df.to_csv(os.path.join(save_dir, 'process_list_autogen.csv'), index=False)
		idx = process_stack.index[i]
		slide = process_stack.loc[idx, 'slide_id']
		print("\n\nprogress: {:.2f}, {}/{}".format(i/total, i, total))
		print('processing {}'.format(slide))
		
		df.loc[idx, 'process'] = 0
		slide_id, _ = os.path.splitext(slide)

		if auto_skip and os.path.isfile(os.path.join(patch_save_dir, slide_id + '.h5')):
			print('{} already exist in destination location, skipped'.format(slide_id))
			df.loc[idx, 'status'] = 'already_exist'
			continue

		# Inialize WSI
		full_path = os.path.join(source, slide)
		WSI_object = WholeSlideImage(full_path, hdf5_file=None)

		if use_default_params:
			current_vis_params = vis_params.copy()
			current_filter_params = filter_params.copy()
			current_seg_params = seg_params.copy()
			current_patch_params = patch_params.copy()
			
		else:
			current_vis_params = {}
			current_filter_params = {}
			current_seg_params = {}
			current_patch_params = {}
			for key in vis_params.keys():
				current_vis_params.update({key: df.loc[idx, key]})

			for key in filter_params.keys():
				current_filter_params.update({key: df.loc[idx, key]})

			for key in seg_params.keys():
				current_seg_params.update({key: df.loc[idx, key]})

			for key in patch_params.keys():
				current_patch_params.update({key: df.loc[idx, key]})

		if current_vis_params['vis_level'] < 0:
			if len(WSI_object.level_dim) == 1:
				current_vis_params['vis_level'] = 0
			
			else:	
				wsi = WSI_object.getOpenSlide()
				best_level = wsi.get_best_level_for_downsample(64) # "closest level": actually next larger (svs) or equally sized level (ndpi) in the slide. 
    #svs normally has less levels and level_downsamples not int. Thus for svs next largest level with a downsample less than user's downsample. 
    #ndpi normally has levels of 2^n of n = 0-7 or 8, so always the exact size.
				current_vis_params['vis_level'] = best_level

		if current_seg_params['seg_level'] < 0:
			if len(WSI_object.level_dim) == 1:
				current_seg_params['seg_level'] = 0
			
			else:
				wsi = WSI_object.getOpenSlide()
				best_level = wsi.get_best_level_for_downsample(64) # uses the downsample in the WSI closest to 64x downsample
				current_seg_params['seg_level'] = best_level
        
		w, h = WSI_object.level_dim[current_seg_params['seg_level']] 
		if w * h > 1e8:
			print('level_dim {} x {} is likely too large for successful segmentation, aborting'.format(w, h))
			df.loc[idx, 'status'] = 'failed_seg'
			continue

		if not process_list:
			df.loc[idx, 'vis_level'] = current_vis_params['vis_level']
			df.loc[idx, 'seg_level'] = current_seg_params['seg_level']

		seg_time_elapsed = -1
		if seg:
            ###*********************************
            ### Modified by Qinghe 23/04/2021
#            WSI_object, seg_time_elapsed = segment(WSI_object, current_seg_params, current_filter_params)
			WSI_object, seg_time_elapsed = segment(WSI_object, current_seg_params, current_filter_params, annotations, annotation_dir, 
                                          slide) 
            ###*********************************

		if save_mask:
			mask = WSI_object.visWSI(**current_vis_params)
#			mask.show()
			mask_path = os.path.join(mask_save_dir, slide_id+'.png')
			mask.save(mask_path)

		patch_time_elapsed = -1 # Default time
		if patch:
			current_patch_params.update({'patch_level': patch_level, 'patch_size': patch_size, 'step_size': step_size, 
										 'save_path': patch_save_dir, 'custom_downsample': custom_downsample})
            ###*********************************
            ### Modified by Qinghe 23/04/2021
            # file_path, patch_time_elapsed = patching(WSI_object = WSI_object, **current_patch_params)
			file_path, patch_time_elapsed = patching(WSI_object = WSI_object, annotations=annotations, **current_patch_params)
            ###*********************************
		
		stitch_time_elapsed = -1
		if stitch:
			file_path = os.path.join(patch_save_dir, slide_id+'.h5')
			heatmap, stitch_time_elapsed = stitching(file_path, downscale=64)
			stitch_path = os.path.join(stitch_save_dir, slide_id+'.png')
			heatmap.save(stitch_path)

		print("segmentation took {} seconds".format(seg_time_elapsed))
		print("patching took {} seconds".format(patch_time_elapsed))
		print("stitching took {} seconds".format(stitch_time_elapsed))
		df.loc[idx, 'status'] = 'processed'

		seg_times += seg_time_elapsed
		patch_times += patch_time_elapsed
		stitch_times += stitch_time_elapsed

	seg_times /= total
	patch_times /= total
	stitch_times /= total

	df.to_csv(os.path.join(save_dir, 'process_list_autogen.csv'), index=False)
	print("average segmentation time in s per slide: {}".format(seg_times))
	print("average patching time in s per slide: {}".format(patch_times))
	print("average stiching time in s per slide: {}".format(stitch_times))
		
	return seg_times, patch_times

#%%
parser = argparse.ArgumentParser(description='seg and patch')
parser.add_argument('--source', type = str,
					help='path to folder containing raw wsi image files')
parser.add_argument('--step_size', type = int, default=256,
                    ###*********************************
                    #Modified by Qinghe 21/04/2021
#                    help='step_size')
					help='step size for x and y at the actual patching level')
                    ###*********************************
parser.add_argument('--patch_size', type = int, default=256,
                    ###*********************************
                    #Modified by Qinghe 21/04/2021
#					help='patch_size')
					help='patch_size for x and y at the actual patching level')
                    ###*********************************
parser.add_argument('--patch', default=False, action='store_true')
parser.add_argument('--seg', default=False, action='store_true')
parser.add_argument('--stitch', default=False, action='store_true')
parser.add_argument('--no_auto_skip', default=True, action='store_false')
parser.add_argument('--save_dir', type=str, default='./results',
					help='directory to save processed data')
parser.add_argument('--preset', default=None, type=str,
					help='predefined profile of default segmentation and filter parameters (.csv)')
parser.add_argument('--patch_level', type=int, default=0, 
                    ###*********************************
                    #Modified by Qinghe 21/04/2021
					#help='downsample level at which to patch')
					help='native downsample level at which to patch (could combine with custom_downsample)')
                    ###*********************************
parser.add_argument('--custom_downsample', type= int, choices=[1,2], default=1, 
					help='custom downscale when native downsample is not available (only tested w/ 2x downscale)')
parser.add_argument('--process_list',  type = str, default=None,
					help='name of list of images to process with parameters (.csv)')
###*********************************
### Modified by Qinghe 04/2021
parser.add_argument('--mask_save_dir',  type = str, default=None,
					help='directory to save segmentated tissue mask')
parser.add_argument('--patch_save_dir',  type = str, default=None,
					help='directory to save patches')
parser.add_argument('--stitch_save_dir',  type = str, default=None,
					help='directory to save stitched png')
parser.add_argument('--use_annotations', default=False, action='store_true',
                    help='import tumor annotation (txt)')
parser.add_argument('--annotation_dir',  type = str, default=None,
					help='directory of annotation coordinate file (.txt)')

args = parser.parse_args()
###*********************************

#%% Modified by Qinghe 04/2021
## Parameters for test
#parser = argparse.ArgumentParser(description='seg and patch')
#args = parser.parse_args()
#
#args.source = "./data/data_tcga_hcc"
#args.step_size = 256
#args.patch_size = 256
#args.patch = True
#args.seg = True
#args.stitch = True
#args.no_auto_skip = True
#args.save_dir = 'results'
#args.preset = None
#args.patch_level = 0
#args.custom_downsample = 2 # most are 40x
#args.process_list = 'process_list_test.csv'
#args.mask_save_dir = './results/test/masks_test'
#args.patch_save_dir = './results/test/patches_test'
#args.stitch_save_dir = './results/test/stitches_test'
#args.use_annotations = False
#args.annotation_dir = './data/annotations'

#%%

if __name__ == '__main__':
####********************************************************************
#     Modified by Qinghe 21/04/2021
#	args = parser.parse_args()

#    patch_save_dir = os.path.join(args.save_dir, 'patches')
#	mask_save_dir = os.path.join(args.save_dir, 'masks')
#	stitch_save_dir = os.path.join(args.save_dir, 'stitches')
	if args.patch_save_dir is None:
		patch_save_dir = os.path.join(args.save_dir, 'patches')
	else: 
		patch_save_dir = args.patch_save_dir
        
	if args.mask_save_dir is None:
		mask_save_dir = os.path.join(args.save_dir, 'masks')
	else: 
		mask_save_dir = args.mask_save_dir
        
	if args.stitch_save_dir is None:
		stitch_save_dir = os.path.join(args.save_dir, 'stitches')
	else: 
		stitch_save_dir = args.stitch_save_dir
####********************************************************************

	if args.process_list:
		process_list = os.path.join(args.save_dir, args.process_list)

	else:
		process_list = None
	
	directories = {'source': args.source, 
				   'save_dir': args.save_dir,
				   'patch_save_dir': patch_save_dir, 
				   'mask_save_dir' : mask_save_dir, 
				   'stitch_save_dir': stitch_save_dir} 


	for key, val in directories.items():
		print("{} : {}".format(key, val))
		if key not in ['source']:
			os.makedirs(val, exist_ok=True)

	seg_params = {'seg_level': -1, 'sthresh': 8, 'mthresh': 7, 'close': 4, 'use_otsu': False}
	filter_params = {'a_t':100, 'a_h': 16, 'max_n_holes':8}
	vis_params = {'vis_level': -1, 'line_thickness': 250}
	patch_params = {'white_thresh': 5, 'black_thresh': 40, 'use_padding': True, 'contour_fn': 'four_pt'}

	if args.preset:
		preset_df = pd.read_csv(os.path.join('presets', args.preset))
		for key in seg_params.keys():
			seg_params[key] = preset_df.loc[0, key]

		for key in filter_params.keys():
			filter_params[key] = preset_df.loc[0, key]

		for key in vis_params.keys():
			vis_params[key] = preset_df.loc[0, key]

		for key in patch_params.keys():
			patch_params[key] = preset_df.loc[0, key]
	
	parameters = {'seg_params': seg_params,
				  'filter_params': filter_params,
	 			  'patch_params': patch_params,
				  'vis_params': vis_params}

	print(parameters)

	seg_times, patch_times = seg_and_patch(**directories, **parameters,
											patch_size = args.patch_size, step_size=args.step_size, 
											seg = args.seg,  use_default_params=False, save_mask = True, 
											stitch= args.stitch, custom_downsample = args.custom_downsample, 
											patch_level=args.patch_level, patch = args.patch,
                                            ####********************************************************************
                                            #Modified by Qinghe 23/04/2021
#											process_list = process_list, auto_skip=args.no_auto_skip)
                                            process_list = process_list, auto_skip=args.no_auto_skip, 
                                            annotations=args.use_annotations, annotation_dir=args.annotation_dir)
                                            ####********************************************************************
    
