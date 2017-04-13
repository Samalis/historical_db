# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import scraper.items as items
from sqlalchemy.orm import sessionmaker
from scraper.models import Agency, Mission, Instrument, db_connect, create_tables
from scraper.spiders import CEOSDB_schema
from rdflib import Graph, Literal, RDF, RDFS, URIRef
from rdflib.namespace import FOAF, OWL

class DatabasePipeline(object):
    """Database pipeline for storing scraped items in the database"""
    def __init__(self):
        """
        Initializes database connection and sessionmaker.
        Creates deals table.
        """
        engine = db_connect()
        create_tables(engine)
        self.Session = sessionmaker(bind=engine)

    def open_spider(self, spider):
        session = self.Session()

        try:
            for instrument in session.query(Instrument).all():
                session.delete(instrument)
            for mission in session.query(Mission).all():
                session.delete(mission)
            for agency in session.query(Agency):
                session.delete(agency)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def process_item(self, item, spider):
        """Save items in the database.

        This method is called for every item pipeline component.

        """
        session = self.Session()

        if isinstance(item, items.Agency):
            object = Agency(**item)
        elif isinstance(item, items.Mission):
            object = Mission(id=item['id'], name=item['name'], full_name=item['full_name'], status=item['status'],
                             launch_date=item['launch_date'], eol_date=item['eol_date'], applications=item['applications'],
                             orbit_type=item['orbit_type'], orbit_period=item['orbit_period'], orbit_sense=item['orbit_sense'],
                             orbit_inclination=item['orbit_inclination'], orbit_altitude=item['orbit_altitude'],
                             orbit_longitude=item['orbit_longitude'], orbit_LST=item['orbit_LST'],
                             repeat_cycle=item['repeat_cycle'])
            for agency_id in item['agencies']:
                agency = session.query(Agency).get(agency_id)
                object.agencies.append(agency)
        elif isinstance(item, items.Instrument):
            object = Instrument(id=item['id'], name=item['name'], full_name=item['full_name'])
            for agency_id in item['agencies']:
                agency = session.query(Agency).get(agency_id)
                object.agencies.append(agency)
        else:
            object = None

        try:
            session.add(object)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

        return item

class OntologyPipeline(object):
    """Ontology pipeline for storing scraped items in an ontology"""
    def __init__(self):
        """
        Initializes database connection and sessionmaker.
        Creates deals table.
        """
        self.g = Graph()
        self.define_subclasses()


    def define_subclasses(self):
        self.g.add((CEOSDB_schema.agencyClass, RDFS.subClassOf, OWL.Thing))
        self.g.add((CEOSDB_schema.missionClass, RDFS.subClassOf, OWL.Thing))
        self.g.add((CEOSDB_schema.instrumentClass, RDFS.subClassOf, OWL.Thing))
        self.g.add((CEOSDB_schema.measurementCategoryClass, RDFS.subClassOf, OWL.Thing))
        self.g.add((CEOSDB_schema.measurementClass, RDFS.subClassOf, OWL.Thing))

    def process_item(self, item, spider):
        """Save items in the database.

        This method is called for every item pipeline component.

        """

        if isinstance(item, items.Agency):
            sa = URIRef("http://ceosdb/agency#" + item['id'])
            self.g.add((sa, RDFS.label, Literal(item['name'])))
            self.g.add((sa, RDF.type, CEOSDB_schema.agencyClass))
            self.g.add((sa, CEOSDB_schema.isFromCountry, Literal(item['country'])))
            self.g.add((sa, FOAF.homepage, URIRef(item['website'])))
        elif isinstance(item, items.Mission):
            mission = URIRef("http://ceosdb/mission#" + item['id'])
            self.g.add((mission, RDFS.label, Literal(item['name'])))
            self.g.add((mission, RDF.type, CEOSDB_schema.missionClass))
            if item['full_name'] is not None:
                self.g.add((mission, CEOSDB_schema.hasFullName, Literal(item['full_name'])))
            for agency_id in item['agencies']:
                self.g.add((mission, CEOSDB_schema.builtBy, URIRef("http://ceosdb/agency#" + str(agency_id))))
            self.g.add((mission, CEOSDB_schema.hasStatus, Literal(item['status'])))
            if item['launch_date'] is not None:
                self.g.add((mission, CEOSDB_schema.hasLaunchDate, Literal(item['launch_date'])))
            if item['eol_date'] is not None:
                self.g.add((mission, CEOSDB_schema.hasEOLDate, Literal(item['eol_date'])))
            self.g.add((mission, CEOSDB_schema.hasApplications, Literal(item['applications'])))
            if item['orbit_type'] != '':
                self.g.add((mission, CEOSDB_schema.hasOrbitType, Literal(item['orbit_type'])))
            if item['orbit_period'] != '':
                self.g.add((mission, CEOSDB_schema.hasOrbitPeriod, Literal(item['orbit_period'])))
            if item['orbit_sense'] != '':
                self.g.add((mission, CEOSDB_schema.hasOrbitSense, Literal(item['orbit_sense'])))
            if item['orbit_inclination'] != '':
                self.g.add((mission, CEOSDB_schema.hasOrbitInclination, Literal(item['orbit_inclination'])))
            if item['orbit_altitude'] != '':
                self.g.add((mission, CEOSDB_schema.hasOrbitAltitude, Literal(item['orbit_altitude'])))
            if item['orbit_longitude'] != '':
                self.g.add((mission, CEOSDB_schema.hasOrbitLongitude, Literal(item['orbit_longitude'])))
            if item['repeat_cycle'] != '':
                self.g.add((mission, CEOSDB_schema.hasRepeatCycle, Literal(item['repeat_cycle'])))
        elif isinstance(item, items.Instrument):
            instrument = URIRef('http://ceosdb/instrument#' + item['id'])
            self.g.add((instrument, RDFS.label, Literal(item['name'])))
            self.g.add((instrument, RDF.type, CEOSDB_schema.instrumentClass))
            if item['full_name'] is not None:
                self.g.add((instrument, CEOSDB_schema.hasFullName, Literal(item['full_name'])))
            for agency_id in item['agencies']:
                self.g.add((instrument, CEOSDB_schema.builtBy, URIRef("http://ceosdb/agency#" + str(agency_id))))

        return item

    def close_spider(self, spider):
        with open('ontology.n3', 'wb') as ont_file:
            ont_file.write(self.g.serialize(format='n3'))