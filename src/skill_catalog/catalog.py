"""Skill catalog: Markdown authority, SQL projection, shared Core RAG.

External skill packages are read-only. Cards are agent-authored descriptions.
"""
import hashlib
import json
import re
from datetime import datetime, timezone


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


class Cards:
    directory = 'cards'
    collection = 'cards'

    def __init__(self, core):
        self.core = core

    def rows(self):
        return self.core.storage.query('SELECT * FROM "{{module}}::cards"', [])['rows']

    def initialize(self):
        marker = self.core.storage.query('SELECT value FROM "{{module}}::metadata" WHERE key=?', ['cards_initialized'])['rows']
        if not marker:
            self.core.documents.prepare(directory=self.directory)
            self.core.storage.execute('INSERT INTO "{{module}}::metadata" VALUES (?,?)', ['cards_initialized', '1'])

    @staticmethod
    def validate(metadata, content):
        for field in ('id', 'title', 'description', 'source_id', 'location'):
            if not isinstance(metadata.get(field), str) or not metadata[field].strip():
                raise ValueError('Skill card requires ' + field)
        if metadata.get('type') != 'skill' or not isinstance(content, str) or not content.strip():
            raise ValueError('A skill card requires type=skill and a nonempty description body')
        for field in ('tags', 'links', 'required_links'):
            values = metadata.get(field, [])
            if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
                raise ValueError(field + ' must be a list of nonempty strings')
            if field != 'tags' and any(not re.fullmatch(r'\[\[[^\[\]\n]+\]\]', v) for v in values):
                raise ValueError(field + ' must contain Obsidian wikilinks')
        for field in ('status', 'updated_at', 'reviewed_revision', 'original_name', 'invocation_name', 'alias_target', 'alias_evidence'):
            if field in metadata and not isinstance(metadata[field], str):
                raise ValueError(field + ' must be text')

        relationship = metadata.get('relationship', 'original')
        if relationship not in {'original', 'native_alias', 'forwarder', 'renamed_copy'}:
            raise ValueError('Unknown skill relationship')
        if relationship in {'native_alias', 'forwarder'}:
            if not metadata.get('alias_target') or not metadata.get('alias_evidence', '').strip():
                raise ValueError('An alias or forwarder needs a target and inspected evidence')
            if not re.fullmatch(r'\[\[[^\[\]\n]+\]\]', metadata['alias_target']):
                raise ValueError('alias_target must be an Obsidian wikilink')

    def capture(self):
        scan = self.core.documents.scan(directory=self.directory, collection=self.collection)
        if not scan.get('complete'):
            raise ValueError('Incomplete card scan; no deletion may be inferred')
        documents, identities = {}, set()
        for doc in scan['documents']:
            meta = doc['metadata']
            self.validate(meta, doc['text'])
            identity = (meta['source_id'], meta['location'])
            if identity in identities or meta['id'] in documents:
                raise ValueError('Duplicate skill installation identity')
            identities.add(identity)
            documents[meta['id']] = doc
        return documents

    @staticmethod
    def summary(doc):
        meta = doc['metadata']
        return {**{k: meta.get(k) for k in ('id','title','description','source_id','location','shell','origin','status','tags','updated_at','source_state','review_required','original_name','invocation_name','relationship','alias_target','alias_evidence')},
                'type': 'skill', 'revision': doc['file_revision'], 'path': doc['path']}

    @staticmethod
    def matches(doc, filters):
        meta = doc['metadata']
        for name, value in (filters or {}).items():
            if name not in {'source_id','shell','origin','tag','status','source_state','original_name','invocation_name','relationship'}:
                raise ValueError('Unknown skill filter: ' + name)
            if name == 'tag':
                if value not in meta.get('tags', []): return False
            elif meta.get(name) != value: return False
        return True

    def read(self, id):
        documents = self.capture()
        if id not in documents:
            raise ValueError('Unknown skill card: ' + id)
        doc = documents[id]
        return {**self.summary(doc), 'content': doc['text'], 'metadata': doc['metadata'],
                'links': doc['metadata'].get('links', []),
                'required_links': doc['metadata'].get('required_links', [])}

    def list(self, filters=None, offset=0, limit=50):
        docs = self.capture()
        values = [self.summary(doc) for doc in docs.values() if self.matches(doc, filters)]
        values.sort(key=lambda v: (v['title'].casefold(), v['id']))
        return {'records': values[offset:offset+limit], 'total': len(values), 'has_more': offset+limit < len(values)}

    def save(self, record, expected_revision=None):
        from .sources import Sources
        record = dict(record)
        record.setdefault('relationship', 'original')
        content = record.pop('content')
        sources = Sources(self.core)
        source = sources.get(record['source_id'])
        snapshot = sources.inspect(record['source_id'], record['location'])
        if record['reviewed_revision'] != snapshot['package_revision']:
            raise ValueError('Source changed; read it before saving the reviewed description')
        ident = record.setdefault('id', digest(encoded([record['source_id'], record['location']]))[:32])
        docs = self.capture()
        old = docs.get(ident)
        if (old['file_revision'] if old else None) != expected_revision:
            raise ValueError('Card changed; read its current revision')
        for other, doc in docs.items():
            if other != ident and (doc['metadata']['source_id'],doc['metadata']['location']) == (record['source_id'],record['location']):
                raise ValueError('This skill installation already has a card: ' + other)
        if old and any(old['metadata'][k] != record[k] for k in ('source_id','location')):
            raise ValueError('Installation identity cannot change')
        metadata = {**record, 'type':'skill', 'updated_at':datetime.now(timezone.utc).isoformat(),
                    'shell':source['shell'],'origin':source['origin'], 'source_state':'present',
                    'review_required':False,'observed_revision':snapshot['package_revision']}
        self.validate(metadata, content)
        path = old['location'] if old else digest(ident)[:32]+'.md'
        self.core.documents.write(directory=self.directory,collection=self.collection,path=path,
            metadata=metadata,text=content,expected_revision=expected_revision)
        try: result=self.reconcile()
        except Exception as exc: result={'index_status':'pending','error':str(exc)}
        return {**self.read(ident),'index':result}

    def rag_document(self, doc):
        return {'key': {'collection': self.collection, 'id':doc['metadata']['id']},
                'revision': doc['revision'], 'text': doc['text'], 'location': doc['path'],
                'metadata': doc['metadata']}

    def reconcile(self):
        docs = self.capture()  # Validate everything before touching derived data.
        previous = {row['id']: row for row in self.rows()}
        plan = self.core.documents.plan(collection=self.collection, documents=list(docs.values()),
            previous=[json.loads(row['document']) for row in previous.values()], complete=True)
        for key in plan['delete']:
            self.core.rag.delete_document(key={'collection': self.collection, 'id':key['id']})
        with self.core.storage.transaction() as tx:
            for key in plan['delete']:
                tx.execute('DELETE FROM "{{module}}::cards" WHERE id=?', [key['id']])
            for ident, doc in docs.items():
                tx.execute('INSERT INTO "{{module}}::cards" (id,document) VALUES (?,?) ON CONFLICT(id) DO UPDATE SET document=excluded.document', [ident,encoded(doc)])
        if not docs:
            return {'index_status':'ready','cards':0,'embedded':0,'deleted':len(plan['delete'])}
        profile = self.core.embeddings.profile()
        profile_revision = digest(encoded(profile))
        errors, embedded = [], 0
        for ident, doc in docs.items():
            stamp = profile_revision + ':' + doc['revision']
            try:
                if previous.get(ident, {}).get('indexed_revision') != stamp:
                    vector = self.core.embeddings.embed_documents(texts=[doc['text']],profile=profile)[0]
                    # Do not acknowledge a stale snapshot if a person edited it meanwhile.
                    current = self.capture().get(ident)
                    if current is None or current['file_revision'] != doc['file_revision']:
                        raise ValueError('Card changed during indexing; reconcile again')
                    self.core.rag.put_vector(document=self.rag_document(doc),vector=vector,profile=profile)
                    embedded += 1
                else:
                    self.core.rag.update_document(document=self.rag_document(doc))
                self.core.storage.execute('UPDATE "{{module}}::cards" SET indexed_revision=?,index_error=NULL WHERE id=?', [stamp,ident])
            except Exception as exc:
                error = str(exc)[:500]
                errors.append({'id':ident,'error':error})
                self.core.storage.execute('UPDATE "{{module}}::cards" SET index_error=? WHERE id=?',[error,ident])
        return {'index_status':'pending' if errors else 'ready','cards':len(docs),'embedded':embedded,'deleted':len(plan['delete']),'errors':errors}

    def search(self, query, filters=None, selection=None, exclude_id=None):
        docs = self.capture()
        # Current file revisions and metadata eligibility are applied before top-N.
        rows = {r['id']:r for r in self.rows()}
        ids = [ident for ident, doc in docs.items() if ident != exclude_id and self.matches(doc,filters)
               and rows.get(ident,{}).get('indexed_revision','') is not None
               and (rows.get(ident,{}).get('indexed_revision') or '').endswith(':'+doc['revision'])]
        response = self.core.rag.search(query=query,collection=self.collection,object_ids=ids,
                                       include_archived=True,**({'selection':selection} if selection is not None else {}))
        current = self.capture()
        result = []
        for hit in response['results']:
            ident = hit['key'][2]
            doc = current.get(ident)
            if doc and doc['revision']==hit['revision'] and self.matches(doc,filters):
                result.append({**self.summary(doc),'distance':hit['distance']})
        return {'results':result,'diagnostics':response['diagnostics'],
                'pending_count':sum(ident not in ids for ident,doc in docs.items() if ident != exclude_id and self.matches(doc,filters))}

    def delete(self, id, expected_revision):
        doc = self.capture().get(id)
        if doc is None:
            raise ValueError('Unknown skill card')
        aliases={id,doc['location'],doc['location'].removesuffix('.md'),doc['path'],doc['path'].removesuffix('.md'),
            'modules/skill_catalog/data/cards/'+doc['location'],
            'modules/skill_catalog/data/cards/'+doc['location'].removesuffix('.md')}
        incoming=[]
        for other,item in self.capture().items():
            refs=item['metadata'].get('links',[])+item['metadata'].get('required_links',[])+([item['metadata']['alias_target']] if item['metadata'].get('alias_target') else [])
            if other!=id and any(ref[2:-2].split('|',1)[0].split('#',1)[0] in aliases for ref in refs):
                incoming.append(other)
        if incoming: raise ValueError('Incoming card links must be resolved first: '+', '.join(incoming))
        self.core.documents.delete(directory=self.directory,path=doc['location'],expected_revision=expected_revision)
        return {'deleted':id,'index':self.reconcile(),'source_skill_untouched':True}

    def status(self):
        docs = self.capture()
        rows = {r['id']:r for r in self.rows()}
        return {'module':'skill_catalog','mode':'skill_cards','cards':len(docs),'background_indexing':False,
                'pending_count':sum(not (rows.get(i,{}).get('indexed_revision') or '').endswith(':'+d['revision']) for i,d in docs.items()),
                'errors':[{'id':r['id'],'error':r['index_error']} for r in rows.values() if r['index_error']],
                'source_skills_read_only':True}

    def refresh(self):
        """Refresh observed source state, preserving authored descriptions and reviews."""
        from .sources import Sources
        sources=Sources(self.core)
        docs=self.capture()
        # Complete all inventories before recording absence. Failed roots abort.
        inventories={sid:{x['location']:x for x in sources.discover(sid)['records']}
                     for sid in {d['metadata']['source_id'] for d in docs.values()}}
        changed=0
        for doc in docs.values():
            meta=dict(doc['metadata']);source=sources.get(meta['source_id'])
            observed=inventories[meta['source_id']].get(meta['location'])
            meta.update(shell=source['shell'],origin=source['origin'],
                source_state='present' if observed else 'missing',
                observed_revision=observed['package_revision'] if observed else None,
                review_required=observed is None or observed['package_revision']!=meta.get('reviewed_revision'))
            if meta!=doc['metadata']:
                self.core.documents.write(directory=self.directory,collection=self.collection,path=doc['location'],
                    metadata=meta,text=doc['text'],expected_revision=doc['file_revision'])
                changed+=1
        return {'updated':changed,'index':self.reconcile()}

    def compare(self, ids):
        from .sources import Sources
        from itertools import combinations
        sources=Sources(self.core)
        items=[]
        for ident in ids:
            card=self.read(ident);meta=card['metadata']
            snapshot=sources.inspect(meta['source_id'],meta['location'])
            items.append({'card':self.summary(self.capture()[ident]),'snapshot':snapshot})
        pairs=[]
        for left,right in combinations(items,2):
            a,b=left['snapshot'],right['snapshot']
            files=sorted(set(a['files'])|set(b['files']))
            pairs.append({'left':left['card']['id'],'right':right['card']['id'],
                'same_instruction':a['instruction_revision']==b['instruction_revision'],
                'same_package':a['package_revision']==b['package_revision'],
                'different_files':[f for f in files if a['files'].get(f)!=b['files'].get(f)]})
        return {'items':[{'card':x['card'],'package_revision':x['snapshot']['package_revision'],'instruction_revision':x['snapshot']['instruction_revision']} for x in items],'pairs':pairs,'interpretation':'Byte equality is evidence; functional overlap requires reading instructions and dependencies.'}

    def related(self, id, selection=None):
        doc=self.read(id)
        return self.search(doc['description']+'\n'+doc['content'],selection=selection,exclude_id=id)
