"""Real child module, Core documents/SQL/RAG and read-only skill fixtures."""
from pathlib import Path
import runpy
import json
import pytest
from contextopus.startup import Application
from contextopus.core.resources import ProcessResources
from contextopus.core.operations import OperationInputError
from contextopus.core.embeddings import default_config
from contextopus.interfaces.web.backend import LibraryBackend

ROOT=Path(__file__).resolve().parents[1]

class Provider:
    def __init__(self):self.calls=[]
    def embed(self,texts,purpose='document'):
        self.calls.append((texts,purpose))
        return [[1.,0.] if 'git' in t.lower() else [0.,1.] for t in texts]
    def tokenizer(self):return lambda text,**kwargs:{'input_ids':text.split()}
    def close(self):pass

@pytest.fixture
def bench(tmp_path):
    build=runpy.run_path(str(ROOT/'scripts/build-module.py'))['build']
    release=build(tmp_path/'release')
    provider=Provider();resources=ProcessResources(provider_factory=lambda config:provider)
    with Application(tmp_path/'data',resources=resources,discover=False) as app:
        config=default_config();config['profile']['dimensions']=2
        app.index.embeddings=config;app.index._generic_table(create=True)
        preview=app.query('core.module_source_plan',{'module':'skill_catalog','source':str(release)})
        app.execute('core.module_install',{'module':'skill_catalog','source':str(release),'source_revision':preview['revision']})
        app.module_manager.start_services()
        source=tmp_path/'installed';source.mkdir()
        app.execute('skill_catalog.source_save',{'id':'codex','root':str(source),'shell':'codex','origin':'user'})
        app.test_provider=provider
        yield app,source
    resources.close()

def skill(source,name='git-reader',body='Read Git history only.',script='print(1)'):
    p=source/name;p.mkdir(exist_ok=True)
    (p/'SKILL.md').write_text('---\nname: git-reader\ndescription: Read Git history.\n---\n\n'+body+'\n',encoding='utf-8')
    (p/'helper.py').write_text(script,encoding='utf-8')
    return name+'/SKILL.md'

def save(app,location,source_id='codex',**values):
    snapshot=app.query('skill_catalog.inspect',{'source_id':source_id,'location':location})
    record={'title':'Git reader','description':'Read Git history without modifications.',
        'source_id':source_id,'location':location,'reviewed_revision':snapshot['package_revision'],
        'file_purposes':{'SKILL.md':'Read-only Git instructions.', 'helper.py':'Synthetic helper source.'},
        'content':'# Git reader\n\nRead Git history. Use for read-only questions. Do not commit.',
        'tags':['git'],'status':'reviewed',**values}
    return app.execute('skill_catalog.save',{'record':record})

def test_discover_save_search_and_native_procedures(bench):
    app,root=bench;location=skill(root)
    before={p.name:p.read_bytes() for p in (root/'git-reader').iterdir()}
    found=app.query('skill_catalog.discover',{'source_id':'codex'})
    assert found['complete'] and len(found['records'])==1
    assert 'instruction' not in found['records'][0]
    card=save(app,location)
    assert card['index']['index_status']=='ready'
    assert Path(card['path']).is_file()
    assert app.test_provider.calls[0][0]==[card['content']]
    hit=app.query('skill_catalog.search',{'query':'Git history'})['results'][0]
    assert hit['id']==card['id'] and 'content' not in hit
    assert app.query('skill_catalog.file_read',{'id':card['id'],'file':'helper.py','expected_revision':card['metadata']['reviewed_revision']})['content']=='print(1)'
    assert {p.name:p.read_bytes() for p in (root/'git-reader').iterdir()}==before
    for proc in ('work','search','catalog'):
        response=app.procedure('skill_catalog/'+proc)
        assert response['operations'] and not response.get('unavailable_operations')
    assert not app.query('skill_catalog.status')['background_indexing']
    app.execute('core.module_disable',{'module':'skill_catalog'})
    app.execute('core.module_enable',{'module':'skill_catalog'});app.module_manager.start_services()
    assert app.query('skill_catalog.read',{'id':card['id']})['revision']==card['revision']

def test_identical_instruction_different_packages_and_related(bench):
    app,root=bench
    a=save(app,skill(root,'one',script='print(1)'))
    b=save(app,skill(root,'two',script='print(2)'))
    pair=app.query('skill_catalog.compare',{'ids':[a['id'],b['id']]})['pairs'][0]
    assert pair['same_instruction'] and not pair['same_package']
    assert pair['different_files']==['helper.py']
    related=app.query('skill_catalog.related',{'id':a['id'],'selection':{'algorithm':'nearest_n','parameters':{'N':1}}})
    assert [x['id'] for x in related['results']]==[b['id']]
    assert app.query('skill_catalog.list')['total']==2

def test_filters_and_web_library(bench,tmp_path):
    app,root=bench;save(app,skill(root))
    other=tmp_path/'claude';other.mkdir()
    app.execute('skill_catalog.source_save',{'id':'claude','root':str(other),'shell':'claude-code','origin':'repository'})
    target=save(app,skill(other),source_id='claude',tags=['audit'])
    filters={'shell':'claude-code','origin':'repository','tag':'audit'}
    result=app.query('skill_catalog.search',{'query':'Git','filters':filters,'selection':{'algorithm':'nearest_n','parameters':{'N':1}}})
    assert [r['id'] for r in result['results']]==[target['id']]
    assert result['diagnostics']['counts']['eligible_documents']==1
    library=LibraryBackend(app)
    assert next(m for m in library.modules()['modules'] if m['id']=='skill_catalog')['available']
    assert library.call('skill_catalog','collections')['filters']
    page=library.call('skill_catalog','records',query='Git',mode='semantic',filters=filters)
    assert page['records'][0]['id']==target['id']
    assert library.call('skill_catalog','record',id=target['id'])['metadata']['location']=='git-reader/SKILL.md'

def test_refresh_preserves_review_and_handles_missing_source(bench):
    app,root=bench;card=save(app,skill(root));p=root/'git-reader/helper.py'
    p.write_text('print(2)')
    app.execute('skill_catalog.refresh')
    changed=app.query('skill_catalog.read',{'id':card['id']})
    assert changed['metadata']['review_required'] and changed['content']==card['content']
    assert changed['metadata']['reviewed_revision']==card['metadata']['reviewed_revision']
    assert changed['revision']!=card['revision']
    (root/'git-reader').rename(root/'renamed')
    app.execute('skill_catalog.refresh')
    missing=app.query('skill_catalog.read',{'id':card['id']})
    assert missing['metadata']['source_state']=='missing'
    root.rename(root.with_name('unavailable'))
    with pytest.raises(Exception,match='missing'):app.execute('skill_catalog.refresh')
    assert app.query('skill_catalog.read',{'id':card['id']})['revision']==missing['revision']

def test_revision_and_read_boundaries(bench,tmp_path):
    app,root=bench;location=skill(root);card=save(app,location)
    with pytest.raises(Exception,match='revision'):save(app,location)
    with pytest.raises(Exception):app.query('skill_catalog.inspect',{'source_id':'codex','location':'../secret/SKILL.md'})
    with pytest.raises(Exception):app.query('skill_catalog.file_read',{'id':card['id'],'file':'../secret','expected_revision':card['metadata']['reviewed_revision']})
    with pytest.raises(Exception):app.execute('skill_catalog.source_save',{'id':'other','root':str(root/'git-reader'),'shell':'x','origin':'x'})
    (root/'escape').symlink_to(tmp_path,target_is_directory=True)
    with pytest.raises(Exception,match='Symlink'):app.query('skill_catalog.discover',{'source_id':'codex'})
    with pytest.raises(Exception):app.execute('skill_catalog.refresh')
    assert app.query('skill_catalog.read',{'id':card['id']})['revision']==card['revision']

def test_link_guard_and_external_card_reconciliation(bench):
    app,root=bench;a=save(app,skill(root,'one'))
    b=save(app,skill(root,'two'),links=['[['+a['id']+']]'])
    with pytest.raises(Exception,match='Incoming'):app.execute('skill_catalog.delete',{'id':a['id'],'expected_revision':a['revision']})
    assert LibraryBackend(app).call('skill_catalog','record',id=b['id'])['links'][0]['key'][-1]==a['id']
    p=Path(b['path']);p.write_text(p.read_text().replace('Read Git history. Use','Review Git changes. Use'))
    assert b['id'] not in [r['id'] for r in app.query('skill_catalog.search',{'query':'Git'})['results']]
    assert app.execute('skill_catalog.reconcile')['embedded']==1
    moved=p.with_name('moved.md');p.rename(moved)
    assert app.execute('skill_catalog.reconcile')['embedded']==0
    moved.unlink();app.execute('skill_catalog.reconcile')
    app.execute('skill_catalog.delete',{'id':a['id'],'expected_revision':a['revision']})
    assert (root/'one/SKILL.md').is_file() and (root/'two/SKILL.md').is_file()

def test_index_failure_retry(bench,monkeypatch):
    app,root=bench;location=skill(root)
    original=app.test_provider.embed
    def fail(*a,**kw):raise RuntimeError('test embedding offline')
    monkeypatch.setattr(app.test_provider,'embed',fail)
    card=save(app,location)
    assert card['index']['index_status']=='pending' and Path(card['path']).is_file()
    monkeypatch.setattr(app.test_provider,'embed',original)
    assert app.execute('skill_catalog.reconcile')['index_status']=='ready'

def test_archive(tmp_path):
    import zipfile
    archive=runpy.run_path(str(ROOT/'scripts/build-module.py'))['build_zip'](tmp_path/'catalog.zip')
    with zipfile.ZipFile(archive) as z:
        assert 'skill_catalog/package/skills/skills/SKILL.md' in z.namelist()
        manifest=json.loads(z.read('skill_catalog/module.json'))
        assert not any('sync' in o['name'] or 'install' in o['name'] for o in manifest['operations'])
    assert Path(str(archive)+'.sha256').is_file()


def test_real_http_library(bench):
    import http.client
    import threading
    from urllib.parse import urlencode
    from contextopus.interfaces.web.server import LibraryServer
    app,root=bench;card=save(app,skill(root))
    server=LibraryServer(app,port=0)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def get(path):
        client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10)
        try:
            client.request('GET',path);response=client.getresponse()
            body=response.read();assert response.status==200,body
            return json.loads(body)
        finally:client.close()
    try:
        assert any(m['id']=='skill_catalog' and m['available'] for m in get('/api/modules')['modules'])
        assert get('/api/collections?module=skill_catalog')['filters']
        args={'module':'skill_catalog','mode':'semantic','query':'Git','filters':json.dumps({'shell':'codex'})}
        assert get('/api/records?'+urlencode(args))['records'][0]['id']==card['id']
        assert get('/api/record?'+urlencode({'module':'skill_catalog','collection':'cards','id':card['id']}))['content']==card['content']
    finally:
        server.shutdown();server.server_close();thread.join(timeout=3)


def test_changed_package_cannot_be_acknowledged_without_new_review(bench):
    app,root=bench;card=save(app,skill(root))
    record={k:card['metadata'][k] for k in ('id','title','description','source_id','location','reviewed_revision','file_purposes')}
    record['content']='Updated description'
    (root/'git-reader/helper.py').write_text('print(99)')
    with pytest.raises(Exception,match='Source changed'):
        app.execute('skill_catalog.save',{'record':record,'expected_revision':card['revision']})
    assert app.query('skill_catalog.read',{'id':card['id']})['revision']==card['revision']


def test_broken_source_and_duplicate_cards_fail_closed(bench):
    app,root=bench;card=save(app,skill(root))
    (root/'git-reader/SKILL.md').write_text('---\nname: [broken\n---\n')
    with pytest.raises(Exception):app.execute('skill_catalog.refresh')
    assert app.query('skill_catalog.read',{'id':card['id']})['revision']==card['revision']
    p=Path(card['path']);p.with_name('duplicate.md').write_bytes(p.read_bytes())
    with pytest.raises(Exception):app.execute('skill_catalog.reconcile')
    assert (root/'git-reader/SKILL.md').is_file()


def test_alias_metadata_evidence_filters_and_delete_guard(bench):
    app,source=bench
    original=save(app,skill(source,'original'))
    alias_location=skill(source,'alias')
    with pytest.raises(OperationInputError) as rejected:
        save(app,alias_location,relationship='native_alias',alias_target='[['+original['id']+']]')
    assert rejected.value.payload['error']['execution_started'] is False
    alias=save(app,alias_location,original_name='git-reader',invocation_name='g',
        relationship='native_alias',alias_target='[['+original['id']+']]',
        alias_evidence='Inspected the synthetic client mapping git-reader=g.')
    rows=app.query('skill_catalog.list',{'filters':{'invocation_name':'g'}})['records']
    assert [r['id'] for r in rows]==[alias['id']]
    assert rows[0]['original_name']=='git-reader'
    library=app.query('skill_catalog.library',{'action':'record','id':alias['id']})
    assert any(link.get('key',[])[-1:]==[original['id']] for link in library['links'])
    with pytest.raises(Exception):
        app.execute('skill_catalog.delete',{'id':original['id'],'expected_revision':original['revision']})
