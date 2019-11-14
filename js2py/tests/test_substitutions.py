import pytest
from unittest import TestCase
from js2py import js2py

class TestMyVisitor(TestCase):
    def setUp(self):
        pass
    def test_postprocess(self):
        data = """function Box2( min, max ) {

	this.min = ( min !== undefined ) ? min : new Vector2( + Infinity, + Infinity );
	this.max = ( max !== undefined ) ? max : new Vector2( - Infinity, - Infinity );

}

Object.assign( Box2.prototype, {

	set: function ( min, max ) {

		this.min.copy( min );
		this.max.copy( max );

		return this;

	}});"""
        js2py(data, postprocess=True)