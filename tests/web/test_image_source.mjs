import test from 'node:test';
import assert from 'node:assert/strict';
import {imageCoordinates} from '../../src/heritage_flood/web/public/image-layers.mjs';

test('retained south-west / north-east raster bounds become clockwise image corners without shifting',()=>{
 const bounds=[[-30.306881474301086,30.55],[-29.5,31.20704581813161]];
 assert.deepEqual(imageCoordinates(bounds),[[30.55,-29.5],[31.20704581813161,-29.5],[31.20704581813161,-30.306881474301086],[30.55,-30.306881474301086]]);
 assert.deepEqual(bounds,[[-30.306881474301086,30.55],[-29.5,31.20704581813161]]);
 assert.throws(()=>imageCoordinates([[null,30],[-29,32]]));
 assert.throws(()=>imageCoordinates([[-29,32],[-31,30]]));
});
