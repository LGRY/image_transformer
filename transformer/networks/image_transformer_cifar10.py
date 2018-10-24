from __future__ import absolute_import
from functools import reduce
import tensorflow as tf

from transformer.layers.attention_blocked import encoder

class ImageTransformerCifar10():
    def __init__(self, is_training=True):
        self.is_training = is_training
        self.num_classes = 10 + 1

    def forward(self, x):
        hidden = 256
        headers = 4
        filters = 64
        query_size = (32, 32)
        key_size = (32, 32)
        with tf.name_scope('stage0'):
            tf.summary.image('input', x, max_outputs=8)
            x = x / 128 - 1
            x = tf.layers.conv2d(x, headers * filters, kernel_size=(7, 7), strides=(2, 2), padding='SAME')

        with tf.name_scope('stage1'):
            _, x = encoder(x, self.is_training, hidden=hidden, headers=headers, filters=filters, query_size=query_size, key_size=key_size)
            distributions, x = encoder(x, self.is_training, hidden=hidden, headers=headers, filters=filters, query_size=query_size, key_size=key_size)
            tf.summary.image('distributions', tf.expand_dims(distributions[0], axis=-1), max_outputs=8)

        with tf.name_scope('stage2'):
            x = tf.layers.max_pooling2d(x, pool_size=(2, 2), strides=(2, 2))
            _, x = encoder(x, self.is_training, hidden=hidden, headers=headers, filters=filters, query_size=query_size, key_size=key_size)
            _, x = encoder(x, self.is_training, hidden=hidden, headers=headers, filters=filters, query_size=query_size, key_size=key_size)

        '''
        with tf.name_scope('stage3'):
            x = tf.layers.max_pooling2d(x, pool_size=(2, 2), strides=(2, 2))
            _, x = encoder(x, self.is_training, hidden=hidden, headers=headers, filters=filters, query_size=query_size, key_size=key_size)
            _, x = encoder(x, self.is_training, hidden=hidden, headers=headers, filters=filters, query_size=query_size, key_size=key_size)
            
        with tf.name_scope('stage4'):
            x = tf.layers.max_pooling2d(x, pool_size=(2, 2), strides=(2, 2))
            _, x = encoder(x, self.is_training, hidden=hidden, headers=headers, filters=filters, query_size=query_size, key_size=key_size)
            _, x = encoder(x, self.is_training, hidden=hidden, headers=headers, filters=filters, query_size=query_size, key_size=key_size)
            x = tf.layers.max_pooling2d(x, pool_size=(2, 2), strides=(2, 2))

        with tf.name_scope('stage5'):
            x = tf.layers.max_pooling2d(x, pool_size=(2, 2), strides=(2, 2))
            _, x = encoder(x, self.is_training, hidden=hidden, headers=headers, filters=filters, query_size=query_size, key_size=key_size)
            _, x = encoder(x, self.is_training, hidden=hidden, headers=headers, filters=filters, query_size=query_size, key_size=key_size)
        '''

        with tf.name_scope('classifier') as name_scope:
            x = tf.reduce_mean(x, [1, 2]) # global average pool
            flattens_size = reduce((lambda i1, i2: i1 * i2), x.shape.as_list()[1:])
            x = tf.reshape(x, [-1, flattens_size])
            x = tf.layers.dense(x, self.num_classes)
            tf.logging.info('image after unit %s: %s', name_scope, x.get_shape())

        return x
