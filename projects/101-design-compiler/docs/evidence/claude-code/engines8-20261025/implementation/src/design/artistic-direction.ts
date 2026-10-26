// Local art direction derived from existing semantic operators. Only candidate-03/04
// operators resolve to a direction; every other profile returns undefined and renders unchanged.
export type ArtisticDirection='EmberReel'|'PlateStudy';
const byOperator:Record<string,ArtisticDirection>={GalleryStage:'EmberReel',StudioIndex:'PlateStudy'};
export const artisticDirectionFor=(hero:string):ArtisticDirection|undefined=>byOperator[hero];
// Media actually selected by each world (credits list exactly these).
export const artisticChoices:Record<ArtisticDirection,(number|string)[]>={
 EmberReel:[120734,'120734-poster',1868396,10258355,1596417,8233676,1004255,1932466],
 PlateStudy:[1665402,1543170,4367047,8594421,1887240,10266737,968657,943245,972271,267]
};
