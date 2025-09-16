// tests/sum.test.js
const { expect } = require('chai');
const { sum } = require('../src/sum');

describe('sum', () => {
  it('adds two numbers', () => {
    expect(sum(2,3)).to.equal(5); // expected 5, but buggy function returns 4
  });
});
