import glob
import json
import os
import shutil
import socket
import time
import warnings

import cv2
import numpy as np
import torch
import torchvision.transforms as transforms
from PIL import Image
from torch.autograd import Variable
from torchsummary import summary

import _init_paths_
import My_Resnet
from VDAOVideo import VDAOVideo

warnings.filterwarnings("ignore")


#######################################################################
# Defining input and output folders
#######################################################################
def define_folders():
    hostname = socket.gethostname()
    dirRead, outputDir = '', ''
    if hostname == 'rafael-Lenovo-Z40-70':  # notebook pessoal
        pass
    elif hostname == 'notesmt':  # notebook SMT
        # Frames are read from the same folder as the features are saved
        dirRead = '/media/storage/VDAO/'
        outputDir = '/media/storage/VDAO/'
    elif hostname == 'teresopolis.smt.ufrj.br':  # teresopolis
        dirRead = "/home/rafael.padilla/workspace/rafael.padilla/"
        outputDir = "/nfs/proc/rafael.padilla/"
    elif hostname.startswith("node") or hostname.startswith("head"):  #nodes do cluster smt
        dirRead = "/home/rafael.padilla/workspace/rafael.padilla/"
        outputDir = "/nfs/proc/rafael.padilla/"
    elif hostname.startswith('taiwan') or hostname.startswith('zermatt'):  # maquina com GPU taiwan
        dirRead = "/home/rafael.padilla/workspace/rafael.padilla/"
        outputDir = "/nfs/proc/rafael.padilla/"
    else:  # Path not defined
        raise Exception('Error: Folder with videos is not defined!')
    return dirRead, outputDir


# Lambda to insert "0" in 1-digit numbers (eg: 4->"04")
l_double_digit = lambda x: '0' + str(x) if len(str(x)) == 1 else str(x)

pooling_sizes = {
    'conv1': 21,
    'residual1': 28,
    'residual2': 28,
    'residual3': 28,
    'residual4': 21,
    'residual5': 21,
    'residual6': 21,
    'residual7': 21,
    'residual8': 14,
    'residual9': 14,
    'residual10': 14,
    'residual11': 14,
    'residual12': 14,
    'residual13': 14,
    'residual14': 7,
    'residual15': 7,
    'residual16': 7,
}


def get_avg_poolings(layer_name):
    return torch.nn.AvgPool2d(pooling_sizes[layer_name])


def get_max_poolings(layer_name):
    return torch.nn.MaxPool2d(pooling_sizes[layer_name])


def get_sizes_features_vector(input_size,
                              layers_to_extract=[
                                  'conv1', 'residual1', 'residual2', 'residual3', 'residual4',
                                  'residual5', 'residual6', 'residual7', 'residual8', 'residual9',
                                  'residual10', 'residual11', 'residual12', 'residual13',
                                  'residual14', 'residual15', 'residual16'
                              ],
                              post_pooling=False):
    '''
    Given the input size and, names of the layers to extract and the need of a post pooling,
    obtain the size of the feature vector.
    * input_size: Size of the input image [height, width, channels] (Ex: [360,640,3])
    * layers_to_extract: List containing the names of layers to extract (Ex: ['conv1', 'residual1', 'residual2'])
    * post_pooling: Boolean informing if a post pooling is needed after extracting feature. If True, the size of the pooling is obtained from the pooling_sizes
    return: torch.Size object containing the dimensions of the output tensor.
    '''
    # Create empty input
    transformations = transforms.Compose([transforms.ToTensor()])
    img = np.zeros(input_size)
    t_img = torch.tensor(transformations(img).unsqueeze(0), dtype=torch.float, device=device)
    # Create feature_map dictionary to store the sizes
    feature_maps_sizes = {}

    # Define a function that will copy the output of a layer
    def get_activation(name):
        def hook(m, i, o):
            # Define pooling
            if post_pooling:
                pooling_size = pooling_sizes[name]
                # Calculate output size with padding = 0 and stride = pooling_size: As in the ICIP implementation
                # [channels,(height-kernel_size+2*padding)/stride)+1,(width-kernel_size+2*padding)/stride)+1]
                pooling_layer = torch.nn.AvgPool2d(pooling_size)
                feature_maps_sizes[name] = pooling_layer(o.data.squeeze()).shape
            else:
                feature_maps_sizes[name] = o.data.squeeze().shape

        return hook

    for layer_name in layers_to_extract:
        # Get layer to add a hook
        layer = resnet_layers_and_extractors[layer_name]
        # Attach that function to our selected layer
        h = layer.register_forward_hook(get_activation(layer_name))
        # pass the image empty by the model
        resnet50(t_img)
        # Detach hook from thelayer
        h.remove()
    # Return the feature vector
    return feature_maps_sizes


def registra_hooks(model, nome_layer, callback):

    if 'conv1' == nome_layer:
        model.add_hook('conv1', 'conv1', None, callback, {
            'layer_name': 'conv1',
            'pooling_layer': None
        })
    elif 'residual1' == nome_layer:
        model.add_hook('residual1', 'layer1', '0', callback, {
            'layer_name': 'residual1',
            'pooling_layer': None
        })
    elif 'residual2' == nome_layer:
        model.add_hook('residual2', 'layer1', '1', callback, {
            'layer_name': 'residual2',
            'pooling_layer': None
        })
    elif 'residual3' == nome_layer:
        model.add_hook('residual3', 'layer1', '2', callback, {
            'layer_name': 'residual3',
            'pooling_layer': None
        })
    elif 'residual4' == nome_layer:
        model.add_hook('residual4', 'layer2', '0', callback, {
            'layer_name': 'residual4',
            'pooling_layer': None
        })
    elif 'residual5' == nome_layer:
        model.add_hook('residual5', 'layer2', '1', callback, {
            'layer_name': 'residual5',
            'pooling_layer': None
        })
    elif 'residual6' == nome_layer:
        model.add_hook('residual6', 'layer2', '2', callback, {
            'layer_name': 'residual6',
            'pooling_layer': None
        })
    elif 'residual7' == nome_layer:
        model.add_hook('residual7', 'layer2', '3', callback, {
            'layer_name': 'residual7',
            'pooling_layer': None
        })
    elif 'residual8' == nome_layer:
        model.add_hook('residual8', 'layer3', '0', callback, {
            'layer_name': 'residual8',
            'pooling_layer': None
        })
    elif 'residual9' == nome_layer:
        model.add_hook('residual9', 'layer3', '1', callback, {
            'layer_name': 'residual9',
            'pooling_layer': None
        })
    elif 'residual10' == nome_layer:
        model.add_hook('residual10', 'layer3', '2', callback, {
            'layer_name': 'residual10',
            'pooling_layer': None
        })
    elif 'residual11' == nome_layer:
        model.add_hook('residual11', 'layer3', '3', callback, {
            'layer_name': 'residual11',
            'pooling_layer': None
        })
    elif 'residual12' == nome_layer:
        model.add_hook('residual12', 'layer3', '4', callback, {
            'layer_name': 'residual12',
            'pooling_layer': None
        })
    elif 'residual13' == nome_layer:
        model.add_hook('residual13', 'layer3', '5', callback, {
            'layer_name': 'residual13',
            'pooling_layer': None
        })
    elif 'residual14' == nome_layer:
        model.add_hook('residual14', 'layer4', '0', callback, {
            'layer_name': 'residual14',
            'pooling_layer': None
        })
    elif 'residual15' == nome_layer:
        model.add_hook('residual15', 'layer4', '1', callback, {
            'layer_name': 'residual15',
            'pooling_layer': None
        })
    elif 'residual16' == nome_layer:
        model.add_hook('residual16', 'layer4', '2', callback, {
            'layer_name': 'residual16',
            'pooling_layer': None
        })


def get_features(model,
                 device,
                 frame,
                 layer_to_extract,
                 resize_input_factor=1,
                 apply_post_pooling=False):
    if next(model.parameters()).is_cuda is False:
        model.to(device)

    frame_height, frame_width, frame_channels = frame.shape[0], frame.shape[1], frame.shape[2]
    size_frame = [frame_height, frame_width, frame_channels]
    # Resize according to the factor
    input_size = [
        int(size_frame[0] / resize_input_factor),
        int(size_frame[1] / resize_input_factor),
        int(size_frame[2])
    ]
    # Define transformations to be used to extract features
    resize_transform = transforms.Resize(input_size[:2])
    normalize_transform = transforms.Normalize(mean=My_Resnet.mean_imagenet,
                                               std=My_Resnet.std_imagenet)
    to_tensor_transform = transforms.ToTensor()
    transformations = transforms.Compose(
        [resize_transform, to_tensor_transform, normalize_transform])

    def features_extracted_callback(parameters):
        def hook(m, i, o):
            assert parameters['layer_name'] == layer_to_extract
            get_features.features_extracted = o.data.squeeze().cpu()

        return hook

    if layer_to_extract not in model.hooks:
        registra_hooks(model, layer_to_extract, features_extracted_callback)

    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    # Transform image and pass it throught the network
    image = Image.fromarray(np.uint8(frame))
    t_img = torch.tensor(transformations(image).unsqueeze(0), dtype=torch.float, device=device)
    model(t_img)
    return get_features.features_extracted


def generate_and_save_features(video_path,
                               dir_to_save_features,
                               prefix_file_name,
                               layers_to_extract,
                               resize_factor=1,
                               pooling_type='avg_pooling'):
    print('Reading frames from video %s' % video_path)
    vid = VDAOVideo(video_path)
    # Get size of the frames
    size_frame = [vid.videoInfo.getHeight(), vid.videoInfo.getWidth(), 3]
    # Resize according to the factor
    input_size = [
        int(size_frame[0] / resize_factor),
        int(size_frame[1] / resize_factor), size_frame[2]
    ]
    # Define transformations to be used to extract features
    resize_transform = transforms.Resize(input_size[:2])
    normalize_transform = transforms.Normalize(mean=My_Resnet.mean_imagenet,
                                               std=My_Resnet.std_imagenet)
    to_tensor_transform = transforms.ToTensor()
    transformations = transforms.Compose(
        [resize_transform, to_tensor_transform, normalize_transform])

    def features_extracted_callback(parameters):
        def hook(m, i, o):
            if parameters['layer_name'] not in layers_to_extract:
                return
            if parameters['pooling_layer'] != None:
                feature_vector = parameters['pooling_layer'](o.data.squeeze())
            else:
                feature_vector = o.data.squeeze()
            feat_path = prefix_file_name.replace('#layerName#', parameters['layer_name']).replace(
                '#frameNumber#', str(frame_num - 1))
            feat_path = os.path.join(dir_to_save_features, parameters['layer_name'], feat_path)
            # Make sure the feature was not created yet que a feature ainda não foi gerada
            assert os.path.isfile(feat_path) is False
            # Save (we must copy the tensor to the cpu, thats why we use the .cpu() function)
            np.save(feat_path, feature_vector.cpu())

        return hook

    # Add hooks on the resnet50
    # If you wish not to use average pooling, set pooling_layer as None, such as:
    # resnet50.add_hook('conv1', 'conv1', None, features_extracted_callback, {layer_name:'conv1', 'pooling_layer':None})
    if pooling_type in ['avg_pooling', 'max_pooling']:
        if pooling_type == 'avg_pooling':
            get_pooling_layer = get_avg_poolings
        elif pooling_type == 'max_pooling':
            get_pooling_layer = get_max_poolings

        if 'conv1' in layers_to_extract:
            resnet50.add_hook('conv1', 'conv1', None, features_extracted_callback, {
                'layer_name': 'conv1',
                'pooling_layer': get_pooling_layer('conv1')
            })
        if 'residual1' in layers_to_extract:
            resnet50.add_hook('residual1', 'layer1', '0', features_extracted_callback, {
                'layer_name': 'residual1',
                'pooling_layer': get_pooling_layer('residual1')
            })
        if 'residual2' in layers_to_extract:
            resnet50.add_hook('residual2', 'layer1', '1', features_extracted_callback, {
                'layer_name': 'residual2',
                'pooling_layer': get_pooling_layer('residual2')
            })
        if 'residual3' in layers_to_extract:
            resnet50.add_hook('residual3', 'layer1', '2', features_extracted_callback, {
                'layer_name': 'residual3',
                'pooling_layer': get_pooling_layer('residual3')
            })
        if 'residual4' in layers_to_extract:
            resnet50.add_hook('residual4', 'layer2', '0', features_extracted_callback, {
                'layer_name': 'residual4',
                'pooling_layer': get_pooling_layer('residual4')
            })
        if 'residual5' in layers_to_extract:
            resnet50.add_hook('residual5', 'layer2', '1', features_extracted_callback, {
                'layer_name': 'residual5',
                'pooling_layer': get_pooling_layer('residual5')
            })
        if 'residual6' in layers_to_extract:
            resnet50.add_hook('residual6', 'layer2', '2', features_extracted_callback, {
                'layer_name': 'residual6',
                'pooling_layer': get_pooling_layer('residual6')
            })
        if 'residual7' in layers_to_extract:
            resnet50.add_hook('residual7', 'layer2', '3', features_extracted_callback, {
                'layer_name': 'residual7',
                'pooling_layer': get_pooling_layer('residual7')
            })
        if 'residual8' in layers_to_extract:
            resnet50.add_hook('residual8', 'layer3', '0', features_extracted_callback, {
                'layer_name': 'residual8',
                'pooling_layer': get_pooling_layer('residual8')
            })
        if 'residual9' in layers_to_extract:
            resnet50.add_hook('residual9', 'layer3', '1', features_extracted_callback, {
                'layer_name': 'residual9',
                'pooling_layer': get_pooling_layer('residual9')
            })
        if 'residual10' in layers_to_extract:
            resnet50.add_hook('residual10', 'layer3', '2', features_extracted_callback, {
                'layer_name': 'residual10',
                'pooling_layer': get_pooling_layer('residual10')
            })
        if 'residual11' in layers_to_extract:
            resnet50.add_hook('residual11', 'layer3', '3', features_extracted_callback, {
                'layer_name': 'residual11',
                'pooling_layer': get_pooling_layer('residual11')
            })
        if 'residual12' in layers_to_extract:
            resnet50.add_hook('residual12', 'layer3', '4', features_extracted_callback, {
                'layer_name': 'residual12',
                'pooling_layer': get_pooling_layer('residual12')
            })
        if 'residual13' in layers_to_extract:
            resnet50.add_hook('residual13', 'layer3', '5', features_extracted_callback, {
                'layer_name': 'residual13',
                'pooling_layer': get_pooling_layer('residual13')
            })
        if 'residual14' in layers_to_extract:
            resnet50.add_hook('residual14', 'layer4', '0', features_extracted_callback, {
                'layer_name': 'residual14',
                'pooling_layer': get_pooling_layer('residual14')
            })
        if 'residual15' in layers_to_extract:
            resnet50.add_hook('residual15', 'layer4', '1', features_extracted_callback, {
                'layer_name': 'residual15',
                'pooling_layer': get_pooling_layer('residual15')
            })
        if 'residual16' in layers_to_extract:
            resnet50.add_hook('residual16', 'layer4', '2', features_extracted_callback, {
                'layer_name': 'residual16',
                'pooling_layer': get_pooling_layer('residual16')
            })
    # Registra hooks
    else:
        assert pooling_type is None

        if 'conv1' in layers_to_extract:
            resnet50.add_hook('conv1', 'conv1', None, features_extracted_callback, {
                'layer_name': 'conv1',
                'pooling_layer': None
            })
        if 'residual1' in layers_to_extract:
            resnet50.add_hook('residual1', 'layer1', '0', features_extracted_callback, {
                'layer_name': 'residual1',
                'pooling_layer': None
            })
        if 'residual2' in layers_to_extract:
            resnet50.add_hook('residual2', 'layer1', '1', features_extracted_callback, {
                'layer_name': 'residual2',
                'pooling_layer': None
            })
        if 'residual3' in layers_to_extract:
            resnet50.add_hook('residual3', 'layer1', '2', features_extracted_callback, {
                'layer_name': 'residual3',
                'pooling_layer': None
            })
        if 'residual4' in layers_to_extract:
            resnet50.add_hook('residual4', 'layer2', '0', features_extracted_callback, {
                'layer_name': 'residual4',
                'pooling_layer': None
            })
        if 'residual5' in layers_to_extract:
            resnet50.add_hook('residual5', 'layer2', '1', features_extracted_callback, {
                'layer_name': 'residual5',
                'pooling_layer': None
            })
        if 'residual6' in layers_to_extract:
            resnet50.add_hook('residual6', 'layer2', '2', features_extracted_callback, {
                'layer_name': 'residual6',
                'pooling_layer': None
            })
        if 'residual7' in layers_to_extract:
            resnet50.add_hook('residual7', 'layer2', '3', features_extracted_callback, {
                'layer_name': 'residual7',
                'pooling_layer': None
            })
        if 'residual8' in layers_to_extract:
            resnet50.add_hook('residual8', 'layer3', '0', features_extracted_callback, {
                'layer_name': 'residual8',
                'pooling_layer': None
            })
        if 'residual9' in layers_to_extract:
            resnet50.add_hook('residual9', 'layer3', '1', features_extracted_callback, {
                'layer_name': 'residual9',
                'pooling_layer': None
            })
        if 'residual10' in layers_to_extract:
            resnet50.add_hook('residual10', 'layer3', '2', features_extracted_callback, {
                'layer_name': 'residual10',
                'pooling_layer': None
            })
        if 'residual11' in layers_to_extract:
            resnet50.add_hook('residual11', 'layer3', '3', features_extracted_callback, {
                'layer_name': 'residual11',
                'pooling_layer': None
            })
        if 'residual12' in layers_to_extract:
            resnet50.add_hook('residual12', 'layer3', '4', features_extracted_callback, {
                'layer_name': 'residual12',
                'pooling_layer': None
            })
        if 'residual13' in layers_to_extract:
            resnet50.add_hook('residual13', 'layer3', '5', features_extracted_callback, {
                'layer_name': 'residual13',
                'pooling_layer': None
            })
        if 'residual14' in layers_to_extract:
            resnet50.add_hook('residual14', 'layer4', '0', features_extracted_callback, {
                'layer_name': 'residual14',
                'pooling_layer': None
            })
        if 'residual15' in layers_to_extract:
            resnet50.add_hook('residual15', 'layer4', '1', features_extracted_callback, {
                'layer_name': 'residual15',
                'pooling_layer': None
            })
        if 'residual16' in layers_to_extract:
            resnet50.add_hook('residual16', 'layer4', '2', features_extracted_callback, {
                'layer_name': 'residual16',
                'pooling_layer': None
            })
    print('Saving frames in %s' % dir_to_save_features)
    if not os.path.isdir(dir_to_save_features):
        os.makedirs(dir_to_save_features)
    total_frames = vid.videoInfo.getNumberOfFrames()
    for frame_num in range(1, total_frames + 1):
        frame = vid.GetFrame(frame_num)
        if not frame[0]:
            raise Exception('Error: Invalid frame!')
        # As frames are retrived as BGR, convert it to RGB
        frame = cv2.cvtColor(frame[1], cv2.COLOR_BGR2RGB)
        # Transform image and pass it throught the network
        image = Image.fromarray(np.uint8(frame))
        t_img = torch.tensor(transformations(image).unsqueeze(0), dtype=torch.float, device=device)
        resnet50(t_img)
    resnet50.remove_all_hooks()


if __name__ == "__main__":
    # Load the resnet50 with pretrained model
    resnet50 = My_Resnet.resnet50(pretrained=True)
    # Define device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # summary(resnet50.to(device), input_size)
    # Set model to evaluation mode
    resnet50.to(device)
    resnet50.eval()
    # Get directories to read frames from and write feature maps
    dir_read, dir_save = define_folders()

    ####################################################################################
    ################################### Definitions ####################################
    ####################################################################################
    # Change here to 'research' or 'object'
    database_type = 'object'
    # Change here 'shortest_distance' or 'dtw'
    alignment_mode = 'shortest_distance'
    layers_to_extract = [
        'conv1', 'residual1', 'residual2', 'residual3', 'residual4', 'residual5', 'residual6',
        'residual7', 'residual8', 'residual9', 'residual10', 'residual11', 'residual12',
        'residual13', 'residual14', 'residual15', 'residual16'
    ]
    layers_to_extract = ['residual3']
    tables_to_process = ['table %s' % l_double_digit(i) for i in range(1, 2)]
    # Parameters
    resize_factor = 2
    # Change here None (no pooling) 'max_pooling' or 'avg_pooling'
    pooling_type = 'max_pooling'
    # Set the name of the directory to save the features
    assert pooling_type in [None, 'avg_pooling', 'max_pooling']
    if pooling_type == 'avg_pooling':
        name_dir = 'avg_pooling'
    elif pooling_type == 'max_pooling':
        name_dir = 'max_pooling'
    elif pooling_type is None:
        name_dir = 'no_pooling'

    start = time.time()
    print('Starting process at: %s' % start)
    print('Main parameters:')
    print('* resize_factor = %f' % resize_factor)
    print('* pooling = %s' % pooling_type)

    dir_videos = os.path.join(dir_read, 'vdao_%s/' % database_type)
    dir_save = os.path.join(dir_save, 'vdao_alignment_%s' % database_type, alignment_mode,
                            'features', name_dir)
    print('Folder to read videos: %s' % dir_videos)
    print('Folder to save features: %s' % dir_save)
    for table_name in tables_to_process:
        print('\nGenerating features from table %s' % table_name)
        # Get all videos within the dir_videos
        print(os.path.join(dir_videos, table_name.replace(' ', '_'), '*', '*.avi'))
        videos_paths = glob.glob(
            os.path.join(dir_videos, table_name.replace(' ', '_'), '*', '*.avi'))
        # Loop through each video
        for video_path in videos_paths:
            # Depending on the video, it is a target or a reference
            if '-Object_' in video_path:
                tag = '-Object_'
                type_feat = 'tar'
            elif '-Reference_' in video_path:
                tag = '-Reference_'
                type_feat = 'ref'
            # Get table number
            table_number = table_name.replace('table ', '')
            # Get Object/Reference video number
            idx = video_path.index(tag)
            object_number = video_path[idx + len(tag):]
            idx = object_number.index('/')
            object_number = object_number[:idx]
            # Create dir chain to store the features of the current video
            dirs = os.path.dirname(video_path).split('/')
            idx = dirs.index(table_name.replace(' ', '_'))
            dir_features_to_save = dir_save
            for i in dirs[idx:]:
                dir_features_to_save = os.path.join(dir_features_to_save, i)
            # For each layer to extract, create directory structure to save the features of the current video
            for layer_name in layers_to_extract:
                dir_features_to_save_layer = os.path.join(dir_features_to_save, layer_name)
                if not os.path.isdir(dir_features_to_save_layer):
                    os.makedirs(dir_features_to_save_layer)
            # Name of the file with the feature is defined as: 'feat_[#name_of_the_video#]_#layer_name#_t#table_number#_#type_feature(ref or tar)#_vid#object_number#_frame#frame_number(starts at 0)#.npy'
            prefix_file_name = f'feat_[%s]_#layerName#_t{table_number}_{type_feat}_vid{object_number}_frame_#frameNumber#.npy' % (
                os.path.basename(video_path).replace('.avi', ''))
            # Get features of the frame from all layers
            generate_and_save_features(video_path,
                                       dir_features_to_save,
                                       prefix_file_name,
                                       layers_to_extract,
                                       resize_factor=resize_factor,
                                       pooling_type=pooling_type)

    end = time.time()
    print('\nFinished process with %s seconds' % (end - start))
