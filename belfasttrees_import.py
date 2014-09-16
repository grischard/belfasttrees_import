#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
belfasttrees_import.py

Converts Belfast City Council's Open Data tree database from BCC's XML to osm.
See http://www.belfastcity.gov.uk/council/Openandlinkeddata/opendatasets.aspx

Freely inspired from https://github.com/scubbx/ogd-treename-splitter

Created by Guillaume Rischard on 2014-03-23.
Copyright (c) 2014 CC-BY.

"""


import xml.sax
import re
import sys
from collections import defaultdict
from xml.sax.saxutils import escape
from pyproj import Proj, transform


def irishgridtowgs84(x, y):
    '''Given a coordinate in Irish x,y, return it in wgs84'''
    irishgrid = Proj("+init=EPSG:29902")
    wgs84 = Proj(proj='latlong',datum='WGS84')
    pos = transform(irishgrid, wgs84, x, y)
    # lat, lon are then pos[1], pos[0]
    return pos[1], pos[0]

def tag(key, value):
    '''Given a key and a value, print osm tag'''
    print '        <tag k=\'{}\' v=\'{}\' />'.format(key, value)


def quotescape(unescapedstring):
    '''Escape quotes to XML entities'''
    return escape(unescapedstring, {"'": "&apos;", '"': '&quot;'})


def detect_genus(species):
    '''Extract the genus from a species'''
    if species == "" or species == " ":
        genus = ""
    else:
        genus = species.split()[0]
    return genus.lower()


def type_from_species(genus):
    '''Guess the tree type (conifer/broad leaved) from genus'''
    conifers = frozenset(['abies',
                          'araucaria',
                          'calocedrus',
                          'cedrus',
                          'chamaecyparis',
                          'cryptomeria',
                          'cupressocyparis',
                          'cupressus',
                          'juniperus',
                          'metasequoia',
                          'picea',
                          'pinus',
                          'platycladus',
                          'pseudotsuga',
                          'sequoiadendron',
                          'taxus',
                          'thuja',
                          'thujopsis',
                          'tsuga'
                          ])
    broad_leaved = frozenset(['tilla',
                              'ulmus',
                              'corylus',
                              'quercus',
                              'nothofagus',
                              'eucalyptus',
                              'gingko',
                              'acer',
                              'aesculus',
                              'ailanthus',
                              'albizia',
                              'alnus',
                              'amelanchier',
                              'betula',
                              'broussonetia',
                              'buxus',
                              'caragana',
                              'carpinus',
                              'castanea',
                              'catalpa',
                              'celtis',
                              'cercidiphyllum',
                              'cercis',
                              'cladrastis',
                              'cornus',
                              'corylus',
                              'cotinus',
                              'cotoneaster',
                              'crataegus',
                              'cydonia',
                              'davidia',
                              'elaeagnus',
                              'eucommia',
                              'exochorda',
                              'fagus',
                              'fontanesia',
                              'frangula',
                              'fraxinus',
                              'ginkgo',
                              'gleditsia',
                              'gymnocladus',
                              'hibiscus',
                              'ilex',
                              'juglans',
                              'koelreuteria',
                              'laburnum',
                              'larix',
                              'liquidambar',
                              'liriodendron',
                              'maclura',
                              'magnolia',
                              'malus',
                              'morus',
                              'ostrya',
                              'parrotia',
                              'paulownia',
                              'phellodendron',
                              'photinia',
                              'platanus',
                              'populus',
                              'prunus',
                              'pterocarya',
                              'pyrus',
                              'quercus',
                              'rhamnus',
                              'rhus',
                              'robinia',
                              'salix',
                              'sambucus',
                              'sophora',
                              'sorbus',
                              'tamarix',
                              'tetradium',
                              'tilia',
                              'toona',
                              'ulmus',
                              'zelkova'
                              ])
    if genus in conifers:
        ttype = "conifer"
    elif genus in broad_leaved:
        ttype = "broad_leaved"
    else:  # unknown genus
        ttype = "ON FIRE! Genus: {}".format(genus)
    return ttype


SPECIES_SUBSTITUTIONS = {'Lawson Cypress': 'Chamaecyparis lawsoniana',
                         'Lawson cypress (type)': 'Chamaecyparis lawsoniana',
                         'Lodgepole Pine': 'Pinus contorta',
                         'Field maple': 'Acer campestre',
                         'Beech (type)': 'Fagus (type)'
                         }
SPECIES_IS_REALLY_A_GENUS = re.compile(r"\(type\)$")


class BelfastTreeContentHandler(xml.sax.ContentHandler):
    '''SAX converter from BCC's tree database to OSM'''
    def __init__(self):
        xml.sax.ContentHandler.__init__(self)
        self.nodeid = 31337
        self.tree = defaultdict(list)  # new tree
        self.species = ''
        self.height = ''
        self.content = ''
        self.treetype = ''
        self.genus = ''

    def startElement(self, name, attrs):
        self.content = ''
        if name == "belfasttrees":
            self.tree = defaultdict(list)  # new tree
            self.species = ''
            self.height = ''
            self.content = ''
            self.treetype = ''
            self.genus = ''

    def characters(self, content):
        self.content += content

    def endElement(self, name):
        if name in ["speciestype",
                    "age",
                    "diameterincentimetres",
                    "spreadradiusinmetres",
                    "longitude",
                    "latitude",
                    "treelocationx",
                    "treelocationy",
                    "treetag",
                    "treeheightinmetres"
                    ]:
            self.tree[name] = self.content  # import those as is
        elif name == "treesurround":
            if self.content in ['Concrete',
                                'Flower Bed',
                                'Paved Brick Paviour',
                                'Tarmac'
                                ]:
                self.tree["denotation"] = "avenue"
            elif self.content in ['Bare Ground',
                                  'Bramble/Briars',
                                  'Grass',
                                  'Shrubs',
                                  'Water',
                                  'Woodland'
                                  ]:
                self.tree["denotation"] = "urban"
            else:
                self.tree["fixme"].append("Denotation")
        elif name == "species":
            if self.content in SPECIES_SUBSTITUTIONS:
                self.tree["species"] = SPECIES_SUBSTITUTIONS[self.content]
            else:
                self.tree["species"] = self.content
        elif name == "belfasttrees":  # tree is done, print everything
            if "latitude" not in self.tree and "longitude" in self.tree:
                raise Exception("Tree without lat/lon!")
            mylat, mylon = irishgridtowgs84(self.tree["treelocationx"], self.tree["treelocationy"])
            print '    <node id=\'-{}\' timestamp=\'2012-05-30T09:25:57\' visible=\'true\' lat=\'{}\' lon=\'{}\'>'.format(self.nodeid, mylat, mylon)
            tag('natural', 'tree')
            # data imported as-is
            if "speciestype" in self.tree:
                if self.tree["speciestype"] not in ['N/A', 'Not known']:
                    tag('genus:en', self.tree["speciestype"])
            if "species" in self.tree:
                if self.tree["species"] not in ['N/A', 'Not known']:
                    self.species = self.tree["species"]
                    self.genus = detect_genus(self.species)
                    self.treetype = type_from_species(self.genus)
                    # special cases
                    if self.species == "Mixed broadleaf":
                        self.tree["denotation"] = "cluster"
                        self.treetype = "broad_leaved"
                        self.species = None
                        self.genus = None
                    elif self.species == "Mixed coniferous":
                        self.tree["denotation"] = "cluster"
                        self.treetype = "coniferous"
                        self.species = None
                        self.genus = None
                    elif self.species in ("Mixed", "Mixed broadleaf and coniferous"):
                        self.tree["denotation"] = "cluster"
                        self.treetype = None
                        self.species = None
                        self.genus = None
                    elif SPECIES_IS_REALLY_A_GENUS.search(self.species):
                        self.species = None  # but genus and type can stay
                    if self.species:
                        tag('species', quotescape(self.tree["species"]))
                    if self.genus:
                        tag('genus', self.genus)
                    if self.treetype:
                        tag('leaf_type', self.treetype)
                    if self.tree["denotation"]:
                        tag('denotation', self.tree["denotation"])
                else:
                    self.tree["fixme"].append("Species, genus and English name")
            if "diameterincentimetres" in self.tree:
                tag('circumference', str(float(self.tree["diameterincentimetres"])/100))
            if "spreadradiusinmetres" in self.tree:
                tag('diameter_crown', self.tree["spreadradiusinmetres"])
            # if "treetag" in self.tree:
            #     if self.tree["species"] != '0':
            #         tag('ref:belfastcitycouncil', self.tree["treetag"])
            if "treeheightinmetres" in self.tree:
                self.height = int(self.tree["treeheightinmetres"].split('.')[0])
                if self.height > 0:
                    tag('height', self.height)
            # if "fixme" in self.tree:
                # tag('fixme', ", ".join(self.tree["fixme"]))
            tag('source', 'Belfast City Council 2012')
            print '    </node>'
            self.nodeid += 1


def main(argv):
    '''Check parameters, open bcc xml file, have it converted, output valid osm xml data'''
    if len(sys.argv) != 2:
        print 'Usage: {} inputfile'.format(str(argv[0]))
        sys.exit(2)
    # otherwise, since the number of arguments is correct:
    inputfile = str(argv[1])
    source = open(inputfile)
    print '<?xml version=\'1.0\' encoding=\'UTF-8\'?>'
    print '<osm version=\'0.6\' upload=\'false\' generator=\'belfasttrees_import.py\'>'
    xml.sax.parse(source, BelfastTreeContentHandler())
    print '</osm>'


if __name__ == '__main__':
    main(sys.argv)
