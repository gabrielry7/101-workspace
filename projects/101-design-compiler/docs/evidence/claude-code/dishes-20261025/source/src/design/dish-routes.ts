export const dishIds=['pizza','pasta','salad','dessert'] as const;
export type DishId=typeof dishIds[number];
export function isDishId(value:string):value is DishId{return dishIds.some(id=>id===value)}
export function dishRoute(root:string,id:string){if(!/^\/b3\/candidate-0[1-4]\/$/.test(root)||!isDishId(id))throw Error('DISH_ROUTE_INVALID');return `${root}carta/${id}/`}
