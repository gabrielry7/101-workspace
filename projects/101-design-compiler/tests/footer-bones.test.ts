import test from 'node:test';
import assert from 'node:assert/strict';
import {parseFooterContent} from '../src/bones/footer/contract.ts';
import {carettaFooter} from '../src/bones/footer/caretta.ts';
import {unionArea} from '../src/bones/footer/measure.ts';

test('footer reference has four directories and five unavailable items without destinations', () => {
  const data = parseFooterContent(carettaFooter);
  assert.equal(data.groups.length, 4);
  const soon = data.groups.flatMap(g => g.items).filter(i => i.state === 'soon');
  assert.equal(soon.length, 5);
  assert.ok(soon.every(i => !('href' in i)));
  assert.equal(data.assistants.length, 5);
});

test('unsafe URLs, duplicate IDs, missing identity and soon destinations are rejected', () => {
  const edit = (fn: (data: any) => void) => {
    const data = structuredClone(carettaFooter); fn(data);
    assert.throws(() => parseFooterContent(data));
  };
  edit(d => { d.groups[0].items[0].href = 'javascript:alert(1)'; });
  edit(d => { d.groups[1].items[0].id = d.groups[0].items[0].id; });
  edit(d => { d.brand.name = ''; });
  edit(d => { d.groups[1].items[0].href = 'https://caretta.so/'; });
  edit(d => { d.groups.pop(); });
});

test('rectangle union clips and never double counts overlapping or nested boxes', () => {
  const boundary = {x: 0, y: 0, width: 100, height: 100};
  assert.equal(unionArea([], boundary), 0);
  assert.equal(unionArea([{x:0,y:0,width:100,height:100},{x:10,y:10,width:10,height:10}], boundary), 10000);
  assert.equal(unionArea([{x:-20,y:-20,width:40,height:40},{x:10,y:10,width:20,height:20}], boundary), 700);
  assert.equal(unionArea([{x:120,y:0,width:20,height:20}], boundary), 0);
});
