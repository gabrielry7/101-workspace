"""Bounded resumable photo intake on the existing tenant/asset authority."""
import base64
import hashlib
import io
import json
from datetime import timedelta, datetime
from uuid import uuid4
from typing import Literal
from fastapi import Depends, Request, HTTPException
from PIL import Image, UnidentifiedImageError
from pydantic import Field
from sqlalchemy import ForeignKey, LargeBinary, String, Text, select, update, delete, func
from sqlalchemy.orm import Mapped, mapped_column
from .models import Base, utcnow
from .social_production import Asset, Strict, Intake, require, future, canonical, owned, MAX_BYTES
from .social_video_contracts import MAX_CLIP_BYTES


class Upload(Base):
    __tablename__='social_uploads'
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    business_id:Mapped[str]=mapped_column(ForeignKey('restaurant_commerce_profiles.business_id'),index=True)
    metadata_json:Mapped[str]=mapped_column(Text)
    data:Mapped[bytes]=mapped_column(LargeBinary,default=b'')
    total:Mapped[int]
    sha256:Mapped[str]=mapped_column(String(64))
    expires_at:Mapped[str]=mapped_column(String(64))
    asset_id:Mapped[str|None]=mapped_column(String(64),nullable=True)


class Begin(Intake):
    data_base64:str=Field(default='',max_length=0)
    total:int=Field(ge=1,le=MAX_CLIP_BYTES)
    sha256:str=Field(pattern=r'^[a-f0-9]{64}$')
    media_kind:Literal['photo','video']='photo'
    shoot_id:str|None=Field(default=None,max_length=64)
    shot_id:Literal['detail','process','finish']|None=None


class Chunk(Strict):
    offset:int=Field(ge=0,le=MAX_CLIP_BYTES)
    data_base64:str=Field(min_length=4,max_length=350000)


def upgrade(engine):
    Upload.__table__.create(engine,checkfirst=True)


def register(app,get_session,scoped_staff):
    from .social_migrations import require_ready
    root='/api/operator/restaurants/{business_id}/social'
    def write(business_id:str,request:Request,session=Depends(get_session)):
        principal = scoped_staff(request,session,business_id,'growth.write')
        require_ready(session)
        return principal
    def read(business_id:str,request:Request,session=Depends(get_session)):
        principal = scoped_staff(request,session,business_id,'growth.read')
        require_ready(session)
        return principal
    def locked(session,business,identifier):
        owned(session,Upload,identifier,business)
        session.execute(update(Upload).where(Upload.id==identifier).values(total=Upload.total))
        row=session.get(Upload,identifier,populate_existing=True)
        require(future(row.expires_at,utcnow()),'upload_expired')
        return row
    def info(row):return {'id':row.id,'received':len(row.data),'total':row.total,'asset_id':row.asset_id}

    @app.get(root+'/assets',dependencies=[Depends(read)])
    def library(business_id:str,session=Depends(get_session)):
        items=[]
        for row in session.execute(select(Asset.id,Asset.metadata_json).where(Asset.business_id==business_id,Asset.revoked==False).limit(200)):
            meta=json.loads(row.metadata_json)
            if meta.get('media_kind','photo')=='photo' and future(meta['expires_at'],utcnow()):items.append({'id':row.id,**meta})
        return {'assets':items}
    @app.post(root+'/uploads',dependencies=[Depends(write)])
    def begin(business_id:str,payload:Begin,session=Depends(get_session)):
        require(future(payload.expires_at.isoformat(),utcnow()),'asset_expired')
        if payload.media_kind=='photo':
            require(payload.total<=MAX_BYTES and not payload.shoot_id and not payload.shot_id,'photo_upload_limit',413)
        else:
            from .social_video_models import Shoot
            require(payload.shoot_id and payload.shot_id,'named_shot_required',422)
            owned(session,Shoot,payload.shoot_id,business_id)
            count=sum(json.loads(encoded).get('shoot_id')==payload.shoot_id for encoded in session.scalars(select(Asset.metadata_json).where(Asset.business_id==business_id)))
            require(count<36,'shoot_take_limit',429)
        # Expiring partial bytes have no immutable-evidence exemption.
        session.execute(delete(Upload).where(Upload.business_id==business_id,Upload.expires_at<=utcnow().isoformat()))
        pending=session.scalar(select(func.count()).select_from(Upload).where(Upload.business_id==business_id,Upload.asset_id==None))
        require(pending<3,'finish_or_cancel_pending_uploads')
        row=Upload(id=uuid4().hex,business_id=business_id,metadata_json=canonical(payload.model_dump(mode='json',exclude={'data_base64','total','sha256'})),
                   total=payload.total,sha256=payload.sha256,data=b'',expires_at=(utcnow()+timedelta(days=1)).isoformat())
        session.add(row);session.commit();return info(row)
    @app.get(root+'/uploads/{upload_id}',dependencies=[Depends(read)])
    def get(business_id:str,upload_id:str,session=Depends(get_session)):
        row=owned(session,Upload,upload_id,business_id)
        require(future(row.expires_at,utcnow()),'upload_expired')
        return info(row)
    @app.delete(root+'/uploads/{upload_id}',dependencies=[Depends(write)])
    def cancel(business_id:str,upload_id:str,session=Depends(get_session)):
        row=owned(session,Upload,upload_id,business_id);session.delete(row);session.commit();return {'cancelled':True}
    @app.put(root+'/uploads/{upload_id}',dependencies=[Depends(write)])
    def chunk(business_id:str,upload_id:str,payload:Chunk,session=Depends(get_session)):
        row=locked(session,business_id,upload_id)
        require(row.asset_id is None,'upload_already_complete')
        try: raw=base64.b64decode(payload.data_base64,validate=True)
        except ValueError:raise HTTPException(422,'invalid_chunk') from None
        require(0<len(raw)<=262144,'chunk_size_limit',413)
        end=payload.offset+len(raw)
        require(end<=row.total,'upload_size_limit',413)
        if payload.offset<len(row.data):
            require(row.data[payload.offset:end]==raw,'chunk_conflict')
        else:
            require(payload.offset==len(row.data),'offset_conflict')
            row.data+=raw
        session.commit();return info(row)
    @app.post(root+'/uploads/{upload_id}/complete')
    def complete(business_id:str,upload_id:str,principal=Depends(write),session=Depends(get_session)):
        row=locked(session,business_id,upload_id)
        if row.asset_id:return {'id':row.asset_id}
        require(len(row.data)==row.total,'upload_incomplete')
        require(hashlib.sha256(row.data).hexdigest()==row.sha256,'upload_hash_mismatch')
        meta=json.loads(row.metadata_json)
        require(future(meta['expires_at'],utcnow()),'asset_expired')
        analysis=poster=None
        if meta.get('media_kind')=='video':
            from .social_video_media import intake
            media,analysis,poster=intake(row.data)
            meta.update(media=media,width=media['width'],height=media['height'],format='MP4_OR_MOV')
        else:
            try:
                with Image.open(io.BytesIO(row.data)) as image:
                    require(image.format in {'JPEG','PNG'},'unsupported_photo',422)
                    require(image.width*image.height<=24_000_000,'image_pixel_limit',422)
                    meta.update(width=image.width,height=image.height,format=image.format)
                    image.verify()
            except (UnidentifiedImageError,OSError,Image.DecompressionBombError):raise HTTPException(422,'invalid_photo') from None
        identifier=uuid4().hex
        meta.update(sha256=row.sha256,uploaded_at=utcnow().isoformat(),actor_id=principal.actor_id)
        session.add(Asset(id=identifier,business_id=business_id,original=row.data,metadata_json=canonical(meta)))
        if analysis is not None:
            from .social_video_models import ClipMedia
            session.flush()
            session.add(ClipMedia(asset_id=identifier,business_id=business_id,analysis=analysis,poster=poster,expires_at=datetime.fromisoformat(meta["expires_at"]).timestamp()))
        row.asset_id=identifier;row.data=b''
        session.commit();return {'id':identifier,**meta}
