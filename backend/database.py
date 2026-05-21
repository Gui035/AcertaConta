import uuid
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, Boolean, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel, EmailStr
from datetime import date
from typing import List

# ── Configuração ──────────────────────────────────────────────────────────────

DATABASE_URL = "sqlite:///./acertaconta.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Modelos SQLAlchemy ────────────────────────────────────────────────────────

participante_table = Table(
    "participantes",
    Base.metadata,
    Column("usuario_id", Integer, ForeignKey("usuarios.id")),
    Column("grupo_id", Integer, ForeignKey("grupos.id")),
)


class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    email = Column(String, unique=True, index=True)
    senha_hash = Column(String)
    grupos = relationship("Grupo", secondary=participante_table, back_populates="participantes")
    grupos_criados = relationship("Grupo", back_populates="criador")


class Grupo(Base):
    __tablename__ = "grupos"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    criador_id = Column(Integer, ForeignKey("usuarios.id"))
    link_convite = Column(String, unique=True, default=lambda: str(uuid.uuid4()))
    criador = relationship("Usuario", back_populates="grupos_criados")
    participantes = relationship("Usuario", secondary=participante_table, back_populates="grupos")
    despesas = relationship("Despesa", back_populates="grupo")


class Despesa(Base):
    __tablename__ = "despesas"
    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String)
    valor = Column(Float)
    data = Column(Date)
    grupo_id = Column(Integer, ForeignKey("grupos.id"))
    pago_por_id = Column(Integer, ForeignKey("usuarios.id"))
    grupo = relationship("Grupo", back_populates="despesas")
    pago_por = relationship("Usuario")
    divisoes = relationship("Divisao", back_populates="despesa")


class Divisao(Base):
    __tablename__ = "divisoes"
    id = Column(Integer, primary_key=True, index=True)
    despesa_id = Column(Integer, ForeignKey("despesas.id"))
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    valor_devido = Column(Float)
    pago = Column(Boolean, default=False)
    despesa = relationship("Despesa", back_populates="divisoes")
    usuario = relationship("Usuario")


Base.metadata.create_all(bind=engine)


# ── Schemas Pydantic ──────────────────────────────────────────────────────────

class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str

class UsuarioOut(BaseModel):
    id: int
    nome: str
    email: str
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    usuario: UsuarioOut

class GrupoCreate(BaseModel):
    nome: str

class GrupoOut(BaseModel):
    id: int
    nome: str
    link_convite: str
    criador_id: int
    participantes: List[UsuarioOut] = []
    class Config:
        from_attributes = True

class DespesaCreate(BaseModel):
    descricao: str
    valor: float
    data: date
    grupo_id: int
    participantes_ids: List[int]

class DivisaoOut(BaseModel):
    id: int
    usuario_id: int
    valor_devido: float
    pago: bool
    usuario: UsuarioOut
    class Config:
        from_attributes = True

class DespesaOut(BaseModel):
    id: int
    descricao: str
    valor: float
    data: date
    grupo_id: int
    pago_por_id: int
    pago_por: UsuarioOut
    divisoes: List[DivisaoOut] = []
    class Config:
        from_attributes = True
