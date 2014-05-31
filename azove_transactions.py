# fork from Ethereum

import re
import rlp
from bitcoin import encode_pubkey
from bitcoin import ecdsa_raw_sign, ecdsa_raw_recover
import utils

tx_structure = [
    ["nonce", "int", 0],
    ["gasprice", "int", 0],
    ["startgas", "int", 0],
    ["to", "addr", ''],
    ["value", "int", 0],
    ["data", "bin", ''],
    ["v", "int", 0],
    ["r", "int", 0],
    ["s", "int", 0],
]


class Transaction(object):

    # nonce,gasprice,startgas,to,value,data,v,r,s
    def __init__(self, nonce, gasprice, startgas, to, value, data, v=0, r=0,
                 s=0):
        self.nonce = nonce
        self.gasprice = gasprice
        self.startgas = startgas
        self.to = to
        self.value = value
        self.data = data
        self.v, self.r, self.s = v, r, s

        # Determine sender
        if self.r and self.s:
            rawhash = utils.sha3(self.serialize(False))
            pub = encode_pubkey(
                ecdsa_raw_recover(rawhash, (self.v, self.r, self.s)),
                'bin')
            self.sender = utils.sha3(pub[1:])[-20:].encode('hex')
        # does not include signature
        else:
            self.sender = 0

    @classmethod
    def deserialize(cls, rlpdata):
        kargs = dict()
        args = rlp.decode(rlpdata)
        assert len(args) in (len(tx_structure), len(tx_structure) - 3)
        # Deserialize all properties
        for i, (name, typ, default) in enumerate(tx_structure):
            if i < len(args):
                kargs[name] = utils.decoders[typ](args[i])
            else:
                kargs[name] = default
        return Transaction(**kargs)

    @classmethod
    def hex_deserialize(cls, hexrlpdata):
        return cls.deserialize(hexrlpdata.decode('hex'))

    def sign(self, key):
        rawhash = utils.sha3(self.serialize(False))
        self.v, self.r, self.s = ecdsa_raw_sign(rawhash, key)
        self.sender = utils.privtoaddr(key)
        return self

    def serialize(self, signed=True):
        o = []
        for i, (name, typ, default) in enumerate(tx_structure):
            o.append(utils.encoders[typ](getattr(self, name)))
        return rlp.encode(o if signed else o[:-3])
 
    def hex_serialize(self, signed=True):
        return self.serialize(signed).encode('hex')

    @property
    def hash(self):
        return utils.sha3(self.serialize())

    def hex_hash(self):
        return self.hash.encode('hex')

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.hash == other.hash

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return '<Transaction(%s)>' % self.hex_hash()[:4]


def contract(nonce, gasprice, startgas, endowment, code, v=0, r=0, s=0):
    tx = Transaction(nonce, gasprice, startgas, '', endowment, code)
    tx.v, tx.r, tx.s = v, r, s
    return tx
