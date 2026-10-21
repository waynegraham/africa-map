/** Validate the authored atlas style against MapLibre 6.15.0's declared spec. */
import {readFile} from 'node:fs/promises';
import {validateStyleMin} from '@maplibre/maplibre-gl-style-spec';
const style=JSON.parse(await readFile(new URL('../src/heritage_flood/web/public/style.json',import.meta.url),'utf8'));
const errors=validateStyleMin(style);
if(errors.length){for(const error of errors)console.error(error.message);process.exitCode=1;}
else console.log('MapLibre atlas style validated: no errors.');
