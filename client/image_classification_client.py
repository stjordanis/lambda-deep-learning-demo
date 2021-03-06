# Copyright 2018 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""A client that performs inferences on a ResNet model using the REST API.

Install nvidia-docker
https://github.com/NVIDIA/nvidia-docker#quick-start

Typical usage example:
docker run --runtime=nvidia -p 8501:8501 \
--name tfserving_classification \
--mount type=bind,source=/home/ubuntu/demo/model/cifar10-resnet32-20180824/export,target=/models/classification \
-e MODEL_NAME=classification -t tensorflow/serving:latest-gpu &

python client/image_classification_client.py
"""

from __future__ import print_function

import base64
import requests
import skimage.io
from skimage.transform import resize
import numpy as np
import json
import matplotlib.pyplot as plt

# The server URL specifies the endpoint of your server running the ResNet
# model with the name "resnet" and using the predict interface.
SERVER_URL = 'http://localhost:8501/v1/models/classification:predict'

# The image URL is the location of the image we should send to the server
# IMAGE_URL = 'https://tensorflow.org/images/blogs/serving/cat.jpg'
IMAGE_PATH = '/home/ubuntu/demo/data/cifar10/test/appaloosa_s_001975.png'


def main():
  # Read the image
  image = skimage.io.imread(IMAGE_PATH, plugin='imageio')

  data = json.dumps({"signature_name": "predict", "instances": image.tolist()})
  headers = {"content-type": "application/json"}

  response = requests.post(SERVER_URL, data=data, headers=headers)
  response.raise_for_status()
  print(response.json())

if __name__ == '__main__':
  main()
