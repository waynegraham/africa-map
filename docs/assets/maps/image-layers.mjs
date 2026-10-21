/** Leaflet-style retained geographic bounds → MapLibre clockwise image corners. */
export function imageCoordinates(bounds){
 if(!Array.isArray(bounds)||bounds.length!==2||bounds.some(p=>!Array.isArray(p)||p.length!==2||p.some(v=>typeof v!=='number'||!Number.isFinite(v))))throw new Error('Invalid raster bounds');
 const [[south,west],[north,east]]=bounds;
 if(south>=north||west>=east||south < -85.051129||north > 85.051129||west < -180||east > 180)throw new Error('Invalid raster extent');
 return [[west,north],[east,north],[east,south],[west,south]];
}

export function setImageLayer(map,id,spec,{visible=true,opacity=0.85,before='institutions'}={}){
 const source=`${id}-source`,image={url:new URL(spec.path,location.href).href,coordinates:imageCoordinates(spec.bounds)};
 if(map.getSource(source))map.getSource(source).updateImage(image);else map.addSource(source,{type:'image',...image});
 if(!map.getLayer(id))map.addLayer({id,type:'raster',source,paint:{'raster-opacity':opacity,'raster-resampling':'nearest','raster-fade-duration':0},layout:{visibility:visible?'visible':'none'}},map.getLayer(before)?before:undefined);
 else map.setLayoutProperty(id,'visibility',visible?'visible':'none');
}
