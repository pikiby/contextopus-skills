"""Request-driven module service; no installed skill is modified or executed."""
import threading
from .catalog import Cards
from .sources import Sources


class Service:
    def __init__(self, core):
        self.core = core
        self.cards = Cards(core)
        self.sources = Sources(core)
        self.lock = threading.RLock()

    def start(self):
        if not self.core.rag.capabilities().get('object_ids'):
            raise RuntimeError('Update Core: skill_catalog requires the shared RAG object_ids capability')
        self.cards.initialize()
        marker = self.core.storage.query('SELECT value FROM "{{module}}::metadata" WHERE key=?',['sources_initialized'])['rows']
        if not marker:
            self.core.documents.prepare(directory='sources')
            self.core.storage.execute('INSERT INTO "{{module}}::metadata" VALUES (?,?)',['sources_initialized','1'])

    def close(self):
        pass

    def source_read(self, id):
        item=self.cards.read(id)['metadata']
        return self.sources.inspect(item['source_id'],item['location'])

    def file_read(self, id, file, expected_revision):
        item=self.cards.read(id)['metadata']
        return self.sources.file_read(item['source_id'],item['location'],file,expected_revision)

    def dispatch(self, operation, arguments, context):
        operations={name:getattr(self.cards,name) for name in ('save','read','list','search','related','compare','refresh','reconcile','delete','status')}
        operations.update(source_list=self.sources.list,source_save=self.sources.save,
            discover=self.sources.discover,inspect=self.sources.inspect,source_read=self.source_read,
            file_read=self.file_read,library=self.library)
        if not operation.startswith('skill_catalog.') or operation.split('.',1)[1] not in operations:
            raise ValueError('Unknown skill catalog operation')
        with self.lock:
            return operations[operation.split('.',1)[1]](**arguments)

    def library(self, action, collection=None, query='', mode='text', type=None, offset=0, limit=50, id=None, filters=None):
        if action=='collections':
            return {'collections':[{'id':'cards','title':'Skills'}],
                'filters':[{'name':x,'label':x.replace('_',' ').title()} for x in ('shell','source_id','origin','tag','status','source_state','original_name','invocation_name','relationship')]}
        if collection not in (None,'','cards'):
            raise ValueError('Unknown skill collection')
        def wire(item): return {**item,'key':['skill_catalog','cards',item['id']]}
        if action=='record':
            item=self.cards.read(id)
            aliases={}
            for ident,doc in self.cards.capture().items():
                for alias in (ident,doc['location'],doc['location'].removesuffix('.md'),doc['path'],doc['path'].removesuffix('.md'),
                              'modules/skill_catalog/data/cards/'+doc['location'],
                              'modules/skill_catalog/data/cards/'+doc['location'].removesuffix('.md')):
                    aliases[alias]=doc['metadata']
            links=[]
            for ref in dict.fromkeys(item['links']+item['required_links']+([item['metadata']['alias_target']] if item['metadata'].get('alias_target') else [])):
                target=ref[2:-2].split('|',1)[0].split('#',1)[0]
                match=aliases.get(target)
                links.append({'key':['skill_catalog','cards',match['id']],'title':match['title']} if match else {'reference':ref,'title':ref})
            return {**wire(item),'links':links}
        if action!='records': raise ValueError('Unknown library action')
        if type and type!='skill':return {'records':[],'total':0,'has_more':False,'types':['skill']}
        diagnostics=None
        if mode=='semantic' and query.strip():
            result=self.cards.search(query,filters);items=result['results'];diagnostics=result['diagnostics']
            warnings=[str(result['pending_count'])+' cards need reconciliation.'] if result['pending_count'] else []
        else:
            items=[self.cards.summary(d) for d in self.cards.capture().values() if self.cards.matches(d,filters)]
            if query:items=[x for x in items if query.casefold() in (' '.join(str(x.get(k) or '') for k in ('title','description','original_name','invocation_name'))).casefold()]
            items.sort(key=lambda x:(x['title'].casefold(),x['id']))
            warnings=[]
        return {'records':[wire(x) for x in items[offset:offset+limit]],'total':len(items),
            'has_more':offset+limit<len(items),'types':['skill'],'diagnostics':diagnostics,'warnings':warnings}


def create_service(core):
    return Service(core)
