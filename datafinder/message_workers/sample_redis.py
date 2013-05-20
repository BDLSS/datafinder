import sys
sys.path.append("/var/www/datafinder/datafinder/lib")
from broadcast import BroadcastToRedis
from HTTP_request import HTTPRequest
sys.path.append("/var/www/datafinder/datafinder/message_workers")
from redis import Redis
from redisqueue import RedisQueue
from solr import SolrConnection
from LogConfigParser import Config
from collections import defaultdict
from solrFields import solr_fields_mapping
import json, rdflib

def gather_document(silo_name, uuid, item_id,  graph):
    #graph = item.get_graph()
    document = defaultdict(list)
    #document['uuid'].append(item.metadata['uuid'])
    document['uuid'].append(uuid)
    document['id'].append(item_id)
    document['silo'].append(silo_name)
    #for (_,p,o) in graph.triples((URIRef(item.uri), None, None)):
    for (_,p,o) in graph.triples((None , None, None)):
        if str(p) in solr_fields_mapping:
            field = solr_fields_mapping[str(p)]
            if field == "aggregatedResource":
                if '/datasets/' in o:
                    fn = unicode(o).split('/datasets/')
                    if len(fn) == 2 and fn[1]:
                        document['filename'].append(unicode(fn[1]).encode("utf-8"))
            if field == "embargoedUntilDate":
                ans = u"%sZ"%unicode(o).split('.')[0]
                document[field].append(unicode(ans).encode("utf-8"))
            else:
                document[field].append(unicode(o).encode("utf-8"))
        else:
            document['text'].append(unicode(o).encode("utf-8"))
    document = dict(document)
    return document

if __name__ == "__main__":
    item_id ='monday'
    silo_name = 'DataFinder'
    #r = Redis()
    c = Config()
    redis_section = "redis"
    worker_section = "worker_solr"
    worker_number = '1'
    worker_section = "worker_solr"
     
    rq = Redis()
    
    
    b = BroadcastToRedis('localhost', 'silochanges')
    b.creation(silo_name , item_id)
    
#    line = rq.spop("{\"_timestamp\": \"2013-05-16T18:03:24.125059\", \"type\": \"c\", \"id\": \"datafinder_1\", \"silo\": \"DataFinder\"}")
    

#    msg = json.loads(line)
    
    user_name = 'admin' 
    password = 'test'
    datastore = HTTPRequest(endpointhost='10.0.1.154')       
    datastore.setRequestUserPass(endpointuser=user_name, endpointpass=password) 
    
    (resp,respdata) = datastore.doHTTP_GET(resource="/" + silo_name +"/states/" + item_id )
    print str(respdata)
    json_data = json.loads(respdata)
    uuid = json_data['state']['metadata']['uuid']
                    
    (resp,respdata) = datastore.doHTTP_GET(resource="/" + silo_name +"/datasets/" + item_id +"/manifest.rdf")
    print respdata
    text_file = open("sample_redis_manifest.rdf", "w")
    text_file.write(respdata)
    text_file.close()
    graph=rdflib.Graph()
    try:
        with open("sample_redis_manifest.rdf", 'r') as f:
           graph.parse(f, base="sample_redis_manifest.rdf")
    except IOError, e:
        pass
#    graph.parse('http://10.0.1.154/'+silo_name +"/datasets/" + item_id +"/manifest.rdf")
#    graph.parse(data=respdata, format="application/rdf+xml")
#    graph.parse(data=respdata, format="n3")
#    graph = respdata
    
    solr = SolrConnection(c.get(worker_section, "solrurl"))
    solr_doc = gather_document('DataFinder' , uuid , item_id,  graph )
    print "solr_doc = gather_document('DataFinder' ,"+ str(uuid)+" , "+ str(item_id)+" , "+str(graph)+" )"
    print repr(solr_doc)
    solr.add(_commit=True, **solr_doc)
    solr.commit()
     
 