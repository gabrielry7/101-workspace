import test from 'node:test';
import assert from 'node:assert/strict';
import {artisticMedia,loadArtisticRestaurantMedia} from '../src/media/artistic-restaurant.ts';

test('artistic library is scoped to 03/04, never the accepted 01/02 or arbitrary ids',async()=>{
 assert.equal((await artisticMedia(1665402,'/b3/candidate-04/')).assets.length,2);
 await assert.rejects(artisticMedia(1665402,'/b3/candidate-01/'),/ART_MEDIA_UNREGISTERED_ROUTE/);
 await assert.rejects(artisticMedia(1665402,'/b3/candidate-02/'),/ART_MEDIA_UNREGISTERED_ROUTE/);
 await assert.rejects(artisticMedia(143799,'/b3/candidate-04/'),/ART_MEDIA_UNREGISTERED_ROUTE/);
});
test('artistic imagery and clips expire through existing gates',async()=>{
 await assert.rejects(artisticMedia(1665402,'/b3/candidate-04/','2099-01-01T00:00:00Z'),/ART_MEDIA_USE_BLOCKED/);
 await assert.rejects(artisticMedia(120734,'/b3/candidate-03/','2099-01-01T00:00:00Z'),/ART_MEDIA_USE_BLOCKED/);
});
test('only byte-verified silent derivatives and extracted poster are presentable',async()=>{
 const data=await loadArtisticRestaurantMedia();assert.equal(data.choices.length,19);
 for(const id of [120734,267]){const {assets}=await artisticMedia(id,'/b3/candidate-03/');assert.equal(assets.length,1);assert.equal(assets[0]!.audio_track,'NONE');assert.ok(!assets[0]!.uri.startsWith('private:'));}
 const poster=await artisticMedia('120734-poster','/b3/candidate-03/');assert.ok(poster.assets.every(a=>a.kind==='image'));
});
