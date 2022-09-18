<?php
namespace ccxt;

// ----------------------------------------------------------------------------

// PLEASE DO NOT EDIT THIS FILE, IT IS GENERATED AND WILL BE OVERWRITTEN:
// https://github.com/ccxt/ccxt/blob/master/CONTRIBUTING.md#how-to-contribute-code

// -----------------------------------------------------------------------------

function test_position($exchange, $position, $symbol, $now) {
    assert ($position);
    assert (is_array($position) && array_key_exists('id', $position));
    assert ($position['id'] === null || gettype($position['id']) === 'string');
    assert (is_array($position) && array_key_exists('timestamp', $position));
    assert ($position['timestamp'] === null || (is_float($position['timestamp']) || is_int($position['timestamp'])));
    assert ($position['timestamp'] === null || $position['timestamp'] > 1230940800000); // 03 Jan 2009 - first cryptocurrency block creation time
    assert ($position['timestamp'] === null || $position['timestamp'] < $now);
    assert (is_array($position) && array_key_exists('datetime', $position));
    assert ($position['datetime'] === $exchange->iso8601 ($position['timestamp']));
    assert (is_array($position) && array_key_exists('symbol', $position));
    assert ($symbol === null || $position['symbol'] === $symbol);
    assert (is_array($position) && array_key_exists('info', $position));
    assert ($position['info']);
}

