"""
Copyright 2018 Lambda Labs. All Rights Reserved.
Licensed under
==========================================================================

Resnet32

Train:
python demo/image_classification.py --mode=train \
--gpu_count=4 --batch_size_per_gpu=256 --epochs=10 \
--piecewise_boundaries=50,75,90 \
--piecewise_lr_decay=1.0,0.1,0.01,0.001 \
--dataset_url=https://s3-us-west-2.amazonaws.com/lambdalabs-files/cifar10.tar.gz \
--dataset_meta=~/demo/data/cifar10/train.csv \
--model_dir=~/demo/model/image_classification_cifar10

Evaluation:
python demo/image_classification.py --mode=eval \
--gpu_count=4 --batch_size_per_gpu=256 --epochs=1 \
--dataset_meta=~/demo/data/cifar10/eval.csv \
--model_dir=~/demo/model/image_classification_cifar10

Infer:
python demo/image_classification.py --mode=infer \
--gpu_count=1 --batch_size_per_gpu=1 --epochs=1 \
--model_dir=~/demo/model/image_classification_cifar10 \
--test_samples=~/demo/data/cifar10/test/appaloosa_s_001975.png,~/demo/data/cifar10/test/domestic_cat_s_001598.png,~/demo/data/cifar10/test/rhea_s_000225.png,~/demo/data/cifar10/test/trucking_rig_s_001216.png

Tune:
python demo/image_classification.py --mode=tune \
--dataset_meta=~/demo/data/cifar10/train.csv \
--model_dir=~/demo/model/image_classification_cifar10 \
--gpu_count=4

Pre-trained Model:
curl https://s3-us-west-2.amazonaws.com/lambdalabs-files/cifar10-resnet32-20180824.tar.gz | tar xvz -C ~/demo/model

python demo/image_classification.py --mode=eval \
--gpu_count=4 --batch_size_per_gpu=256 --epochs=1 \
--augmenter_speed_mode \
--dataset_meta=~/demo/data/cifar10/eval.csv \
--model_dir=~/demo/model/cifar10-resnet32-20180824

Train with synthetic data:
python demo/image_classification.py \
--mode=train \
--gpu_count=4 --batch_size_per_gpu=64 --epochs=1000 --piecewise_boundaries=10 \
--network=resnet50 \
--inputter=image_classification_syn_inputter \
--augmenter="" \
--image_height=224 --image_width=224 --num_classes=120 \
--model_dir=~/demo/model/image_classification_StanfordDog120

Transfer Learning:
(mkdir ~/demo/model/resnet_v2_50_2017_04_14;
curl http://download.tensorflow.org/models/resnet_v2_50_2017_04_14.tar.gz | tar xvz -C ~/demo/model/resnet_v2_50_2017_04_14)

python demo/image_classification.py --mode=train \
--gpu_count=4 --batch_size_per_gpu=64 --epochs=20 \
--piecewise_boundaries=10 \
--piecewise_lr_decay=1.0,0.1 \
--network=resnet50 \
--augmenter=vgg_augmenter \
--image_height=224 --image_width=224 --num_classes=120 \
--dataset_meta=~/demo/data/StanfordDogs120/train.csv \
--dataset_url=https://s3-us-west-2.amazonaws.com/lambdalabs-files/StanfordDogs120.tar.gz \
--model_dir=~/demo/model/image_classification_StanfordDog120 \
--pretrained_dir=~/demo/model/resnet_v2_50_2017_04_14 \
--skip_pretrained_var="resnet_v2_50/logits,global_step" \
--trainable_vars="resnet_v2_50/logits"

python demo/image_classification.py \
--mode=eval \
--gpu_count=4 --batch_size_per_gpu=64 --epochs=1 \
--network=resnet50 \
--augmenter=vgg_augmenter \
--image_height=224 --image_width=224 --num_classes=120 \
--dataset_meta=~/demo/data/StanfordDogs120/eval.csv \
--model_dir=~/demo/model/image_classification_StanfordDog120
"""
import sys
import os
import argparse
import importlib


def main():

  sys.path.append('.')

  from source.tool import downloader
  from source.tool import tuner
  from source.tool import config_parser
  from source.config import Config
  from source.config import InputterConfig
  from source.config import ModelerConfig
  from source.config import RunnerConfig

  parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  parser.add_argument("--augmenter",
                      type=str,
                      help="Name of the augmenter",
                      default="cifar_augmenter")
  parser.add_argument("--network", choices=["resnet32", "resnet50"],
                      type=str,
                      help="Choose a network architecture",
                      default="resnet32")
  parser.add_argument("--mode", choices=["train", "eval", "infer", "tune"],
                      type=str,
                      help="Choose a job mode from train, eval, and infer.",
                      default="train")
  parser.add_argument("--dataset_meta", type=str,
                      help="Path to dataset's csv meta file",
                      default="")
  parser.add_argument("--batch_size_per_gpu",
                      help="Number of images on each GPU.",
                      type=int,
                      default=128)
  parser.add_argument("--gpu_count",
                      help="Number of GPUs.",
                      type=int,
                      default=4)
  parser.add_argument("--epochs",
                      help="Number of epochs.",
                      type=int,
                      default=5)
  parser.add_argument("--num_classes",
                      help="Number of classes.",
                      type=int,
                      default=10)
  parser.add_argument("--image_height",
                      help="Image height.",
                      type=int,
                      default=32)
  parser.add_argument("--image_width",
                      help="Image width.",
                      type=int,
                      default=32)
  parser.add_argument("--image_depth",
                      help="Number of color channels.",
                      type=int,
                      default=3)
  parser.add_argument("--model_dir",
                      help="Directory to save mode",
                      type=str,
                      default=os.path.join(
                        os.environ['HOME'],
                        "demo/model/image_classification_cifar10"))
  parser.add_argument("--learning_rate",
                      help="Initial learning rate in training.",
                      type=float,
                      default=0.5)
  parser.add_argument("--piecewise_boundaries",
                      help="Epochs to decay learning rate",
                      default="2")
  parser.add_argument("--piecewise_lr_decay",
                      help="Decay ratio for learning rate",
                      default="1.0,0.1")
  parser.add_argument("--optimizer",
                      help="Name of optimizer",
                      choices=["adadelta", "adagrad", "adam", "ftrl",
                               "momentum", "rmsprop", "sgd"],
                      default="momentum")
  parser.add_argument("--log_every_n_iter",
                      help="Number of steps to log",
                      type=int,
                      default=2)
  parser.add_argument("--save_summary_steps",
                      help="Number of steps to save summary.",
                      type=int,
                      default=2)
  parser.add_argument("--save_checkpoints_steps",
                      help="Number of steps to save checkpoints",
                      type=int,
                      default=100)
  parser.add_argument("--keep_checkpoint_max",
                      help="Maximum number of checkpoints to save.",
                      type=int,
                      default=1)
  parser.add_argument("--class_names",
                      help="List of class names.",
                      default="airplane,automobile,bird,\
                               cat,deer,dog,frog,horse,ship,truck")
  parser.add_argument("--test_samples",
                      help="A string of comma seperated testing data. "
                      "Must be provided for infer mode.",
                      type=str)
  parser.add_argument("--summary_names",
                      help="A string of comma seperated names for summary",
                      type=str,
                      default="loss,accuracy,learning_rate")
  parser.add_argument("--dataset_url",
                      help="URL for downloading data",
                      default="")
  parser.add_argument("--pretrained_dir",
                      help="Path to pretrained network for transfer learning.",
                      type=str,
                      default="")
  parser.add_argument("--skip_pretrained_var",
                      help="Variables to skip in restoring from \
                            pretrained model (for transfer learning).",
                      type=str,
                      default="")
  parser.add_argument("--trainable_vars",
                      help="List of trainable Variables. \
                           If None all variables in TRAINABLE_VARIABLES \
                           will be trained, subjected to the ones \
                           blacklisted by skip_trainable_vars.",
                      type=str,
                      default="")
  parser.add_argument("--skip_trainable_vars",
                      help="List of blacklisted trainable Variables.",
                      type=str,
                      default="")
  parser.add_argument("--skip_l2_loss_vars",
                      help="List of blacklisted trainable Variables for L2 \
                            regularization.",
                      type=str,
                      default="BatchNorm,preact,postnorm")
  parser.add_argument("--train_callbacks",
                      help="List of callbacks in training.",
                      type=str,
                      default="train_basic,train_loss,train_accuracy,train_speed,train_summary")
  parser.add_argument("--eval_callbacks",
                      help="List of callbacks in evaluation.",
                      type=str,
                      default="eval_basic,eval_loss,eval_accuracy,eval_speed,eval_summary")
  parser.add_argument("--infer_callbacks",
                      help="List of callbacks in inference.",
                      type=str,
                      default="infer_basic,infer_display_image_classification")

  config = parser.parse_args()

  config = config_parser.prepare(config)

  # Download data if necessary
  if config.mode != "infer":
    if not os.path.exists(config.dataset_meta):
      downloader.download_and_extract(config.dataset_meta,
                                      config.dataset_url, False)
    else:
      print("Found " + config.dataset_meta + ".")

  if config.mode == "tune":
    tuner.tune(config)
  else:

    """
    An application owns a runner.
    Runner: Distributes a job across devices, schedules the excution.
            It owns an inputter and a modeler.
    Inputter: Handles the data pipeline.
              It (optionally) owns a data augmenter.
    Modeler: Creates functions for network, loss, optimization and evaluation.
             It owns a network and a list of callbacks as inputs.
    """

    # Create configs
    general_config = Config(
      mode=config.mode,
      batch_size_per_gpu=config.batch_size_per_gpu,
      gpu_count=config.gpu_count)

    inputter_config = InputterConfig(
      general_config,
      epochs=config.epochs,
      dataset_meta=config.dataset_meta,
      test_samples=config.test_samples,
      image_height=config.image_height,
      image_width=config.image_width,
      image_depth=config.image_depth,
      num_classes=config.num_classes)

    modeler_config = ModelerConfig(
      general_config,
      optimizer=config.optimizer,
      learning_rate=config.learning_rate,
      trainable_vars=config.trainable_vars,
      skip_trainable_vars=config.skip_trainable_vars,
      piecewise_boundaries=config.piecewise_boundaries,
      piecewise_lr_decay=config.piecewise_lr_decay,
      skip_l2_loss_vars=config.skip_l2_loss_vars,
      num_classes=config.num_classes)

    runner_config = RunnerConfig(
      general_config,
      model_dir=config.model_dir,
      summary_names=config.summary_names,
      log_every_n_iter=config.log_every_n_iter,
      save_summary_steps=config.save_summary_steps,
      pretrained_dir=config.pretrained_dir,
      skip_pretrained_var=config.skip_pretrained_var,
      save_checkpoints_steps=config.save_checkpoints_steps,
      keep_checkpoint_max=config.keep_checkpoint_max,
      train_callbacks=config.train_callbacks,
      eval_callbacks=config.eval_callbacks,
      infer_callbacks=config.infer_callbacks)

    callback_config = runner_config

    augmenter = (None if not config.augmenter else
                 importlib.import_module(
                  "source.augmenter." + config.augmenter))

    net = getattr(importlib.import_module(
      "source.network." + config.network), "net")

    if config.mode == "train":
      callback_names = config.train_callbacks
    elif config.mode == "eval":
      callback_names = config.eval_callbacks
    elif config.mode == "infer":
      callback_names = config.infer_callbacks

    callbacks = []
    for name in callback_names:
      callback = importlib.import_module(
        "source.callback." + name).build(
        callback_config)
      callbacks.append(callback)

    inputter = importlib.import_module(
      "source.inputter.image_classification_csv_inputter").build(
      inputter_config, augmenter)

    modeler = importlib.import_module(
      "source.modeler.image_classification_modeler").build(
      modeler_config, net)

    runner = importlib.import_module(
      "source.runner.parameter_server_runner").build(
      runner_config, inputter, modeler, callbacks)

    # Run application
    runner.run()


if __name__ == "__main__":
  main()
