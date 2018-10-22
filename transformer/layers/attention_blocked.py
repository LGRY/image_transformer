# -*- coding: utf-8 -*-
from __future__ import absolute_import

import tensorflow as tf

from transformer.ops.unrolling import unroll, reroll, pad

# scaled dot-product attention
def attention(query, key, value, query_size=(4, 4), key_size=(8, 8)):
    batch, height, width, depth = query.shape.as_list()
    _, _, _, value_depth = value.shape.as_list()

    padding_kernel_size = ((key_size[0] - query_size[0]) * 2, (key_size[1] - query_size[1]) * 2)

    unrolled_query = unroll(query, kernel_size=query_size, strides=query_size)
    unrolled_query = tf.reshape(query, (-1, query_size[0] * query_size[1], depth))

    unrolled_key = unroll(pad(key, kernel_size=padding_kernel_size), kernel_size=key_size, strides=query_size)
    unrolled_key = tf.reshape(unrolled_key, (-1, key_size[0] * key_size[1], depth))

    unrolled_value = unroll(pad(value, kernel_size=padding_kernel_size), kernel_size=key_size, strides=query_size)
    unrolled_value = tf.reshape(unrolled_value, (-1, key_size[0] * key_size[1], value_depth))

    tf.logging.debug('attention tensor query: %s', unrolled_query.get_shape())
    tf.logging.debug('attention tensor key:   %s', unrolled_key.get_shape())
    tf.logging.debug('attention tensor value: %s', unrolled_value.get_shape())

    distribution = tf.matmul(unrolled_query, tf.transpose(unrolled_key, perm=[0, 2, 1]))
    distribution = tf.nn.softmax(distribution / tf.sqrt(float(depth)), axis=-1)
    tf.logging.debug('attention tensor distribution: %s', distribution.get_shape())

    response = tf.matmul(distribution, unrolled_value)
    tf.logging.debug('attention tensor response: %s', response.get_shape())

    response = reroll(response, width, height, value_depth, query_size, query_size)
    tf.logging.debug('attention tensor reshaped response: %s', response.get_shape())

    return distribution, response

def self_attention(tensor, filters=64, query_size=(4, 4), key_size=(8, 8)):
    query = tf.layers.conv2d(tensor, filters, kernel_size=(1, 1))
    key = tf.layers.conv2d(tensor, filters, kernel_size=(1, 1))
    value = tf.layers.conv2d(tensor, filters, kernel_size=(1, 1))
    
    return attention(query, key, value, query_size, key_size)

def multi_head_attention(tensor, headers=8, filters=64, query_size=(4, 4), key_size=(8, 8)):
    responses = []
    for _ in range(headers):
        _, response = self_attention(tensor, filters, query_size, key_size)
        responses.append(response)
        
    return tf.concat(responses, axis=-1)

def _residual(tensor, orig_tensor, is_training):
    with tf.name_scope('residual') as name_scope:
        if tensor.shape[1:-1] != orig_tensor.shape[1:-1]:
            orig_tensor = tf.layers.conv2d(orig_tensor, headers * filters, kernel_size=(1, 1))
        if tensor.shape[1:] == orig_tensor.shape[1:]:
            tensor = tf.add(tensor, orig_tensor)
        else:
            tensor = tf.concat([tensor, orig_tensor], axis=-1)
        tensor = tf.layers.batch_normalization(tensor, renorm=True, fused=True, training=is_training)
    return tensor

def encoder(tensor, is_training, hidden=1024, headers=8, filters=64, query_size=(4, 4), key_size=(8, 8)):
    orig_tensor = tensor
    with tf.name_scope('multi_head_attention') as name_scope:
        tensor = multi_head_attention(tensor, headers, filters, query_size, key_size)
        tf.logging.info('image after unit %s: %s', name_scope, tensor.get_shape())
        tensor = _residual(tensor, orig_tensor, is_training)
        tf.logging.info('image after unit %s: %s', name_scope, tensor.get_shape())

    orig_tensor = tensor
    with tf.name_scope('position-wise_feed-forward') as name_scope:
        tensor = tf.layers.conv2d(tensor, hidden, kernel_size=(1, 1))
        tensor = tf.nn.relu(tensor)
        tensor = tf.layers.conv2d(tensor, hidden, kernel_size=(1, 1))
        tf.logging.info('image after unit %s: %s', name_scope, tensor.get_shape())

        tensor = _residual(tensor, orig_tensor, is_training)
        tf.logging.info('image after unit %s: %s', name_scope, tensor.get_shape())

    return tensor
