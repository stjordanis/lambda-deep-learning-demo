"""
Copyright 2018 Lambda Labs. All Rights Reserved.
Licensed under
==========================================================================

"""
import tensorflow as tf

from .modeler import Modeler

rnn = tf.contrib.rnn


class TextGenerationModeler(Modeler):
  def __init__(self, config, net):
    super(TextGenerationModeler, self).__init__(config, net)
    self.grad_clip = 5.

  def get_dataset_info(self, inputter):
    self.seq_length = inputter.get_max_length()
    self.num_samples = inputter.get_num_samples()
    self.vocab_size = inputter.get_vocab_size()
    self.items = inputter.get_items()
    self.embd = inputter.get_embd()

  def create_nonreplicated_fn(self):
    self.global_step = tf.train.get_or_create_global_step()
    if self.config.mode == "train":
      self.learning_rate = self.create_learning_rate_fn(self.global_step)

  def create_graph_fn(self, inputs):
    return self.net(inputs, self.feed_dict_seq, self.seq_length,
                    self.config.batch_size_per_gpu, self.vocab_size,
                    self.embd,
                    mode=self.config.mode)

  def create_eval_metrics_fn(self, logits, labels):
    classes = tf.argmax(logits, axis=1, output_type=tf.int32)
    equality = tf.equal(classes, tf.reshape(labels, [-1]))
    accuracy = tf.reduce_mean(tf.cast(equality, tf.float32))
    return accuracy

  def create_loss_fn(self, logits, labels):

      self.gether_train_vars()

      loss_cross_entropy = tf.reduce_mean(
        tf.nn.sparse_softmax_cross_entropy_with_logits(
          logits=logits, labels=tf.reshape(labels, [-1])))

      loss = tf.identity(loss_cross_entropy, "total_loss")

      return loss

  def model_fn(self, x, device_id=None):
    if self.config.mode == "export":
      inputs = x
      input_item, c0, h0, c1, h1 = inputs
    else:
      inputs = x[0]
      labels = x[1]

    logits, probabilities, last_state, inputs = \
        self.create_graph_fn(inputs)

    if self.config.mode == "train":
      loss = self.create_loss_fn(logits, labels)
      grads = self.create_grad_fn(loss, self.grad_clip)
      accuracy = self.create_eval_metrics_fn(logits, labels)
      return {"loss": loss,
              "grads": grads,
              "accuracy": accuracy,
              "learning_rate": self.learning_rate}
    elif self.config.mode == "eval":
      loss = self.create_loss_fn(logits, labels)
      accuracy = self.create_eval_metrics_fn(
        logits, labels)
      return {"loss": loss,
              "accuracy": accuracy}
    elif self.config.mode == "infer":
      return {"inputs": inputs,
              "logits": logits,
              "probabilities": probabilities,
              "items": tf.convert_to_tensor(self.items),
              "last_state": last_state}
    elif self.config.mode == "export":
      # The vocabulary (TODO: store this on client side?)
      items = tf.identity(
        tf.expand_dims(tf.convert_to_tensor(self.items), axis=0), name="items")

      # The prediction
      output_probabilities = tf.identity(
        tf.expand_dims(probabilities, axis=0), name="output_probabilities")

      # The state of memory cells
      output_last_state = tf.identity(
        tf.expand_dims(last_state, axis=0), name="output_last_state")

      return output_probabilities, output_last_state, items

def build(config, net):
  return TextGenerationModeler(config, net)
