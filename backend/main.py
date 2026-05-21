import uuid
import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import FileResponse
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session

from database import (
    get_db, Usuario, Grupo, Despesa, Divisao,
    UsuarioCreate, UsuarioOut, Token,
    GrupoCreate, GrupoOut,
    DespesaCreate, DespesaOut,
)

# ── Segurança ─────────────────────────────────────────────────────────────────

SECRET_KEY = "acertaconta-secret-key-2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def hash_senha(senha: str):
    return pwd_context.hash(senha)

def verificar_senha(senha: str, hash: str):
    return pwd_context.verify(senha, hash)

def criar_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_usuario_atual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Token invalido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido")
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado")
    return usuario


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="AcertaConta API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/auth/cadastro", response_model=Token)
def cadastro(dados: UsuarioCreate, db: Session = Depends(get_db)):
    if db.query(Usuario).filter(Usuario.email == dados.email).first():
        raise HTTPException(status_code=400, detail="E-mail ja cadastrado")
    usuario = Usuario(nome=dados.nome, email=dados.email, senha_hash=hash_senha(dados.senha))
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    token = criar_token({"sub": usuario.email})
    return {"access_token": token, "token_type": "bearer", "usuario": usuario}

@app.post("/auth/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == form.username).first()
    if not usuario or not verificar_senha(form.password, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    token = criar_token({"sub": usuario.email})
    return {"access_token": token, "token_type": "bearer", "usuario": usuario}

@app.get("/auth/me", response_model=UsuarioOut)
def me(usuario: Usuario = Depends(get_usuario_atual)):
    return usuario


# ── Grupos ────────────────────────────────────────────────────────────────────

@app.post("/grupos", response_model=GrupoOut)
def criar_grupo(dados: GrupoCreate, usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    grupo = Grupo(nome=dados.nome, criador_id=usuario.id, link_convite=str(uuid.uuid4()))
    grupo.participantes.append(usuario)
    db.add(grupo)
    db.commit()
    db.refresh(grupo)
    return grupo

@app.get("/grupos", response_model=List[GrupoOut])
def listar_grupos(usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    return usuario.grupos

@app.get("/grupos/{grupo_id}", response_model=GrupoOut)
def obter_grupo(grupo_id: int, usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    grupo = db.query(Grupo).filter(Grupo.id == grupo_id).first()
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo nao encontrado")
    return grupo

@app.post("/grupos/entrar/{link_convite}", response_model=GrupoOut)
def entrar_grupo(link_convite: str, usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    grupo = db.query(Grupo).filter(Grupo.link_convite == link_convite).first()
    if not grupo:
        raise HTTPException(status_code=404, detail="Link invalido")
    if usuario not in grupo.participantes:
        grupo.participantes.append(usuario)
        db.commit()
        db.refresh(grupo)
    return grupo


# ── Despesas ──────────────────────────────────────────────────────────────────

@app.post("/despesas", response_model=DespesaOut)
def registrar_despesa(dados: DespesaCreate, usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    grupo = db.query(Grupo).filter(Grupo.id == dados.grupo_id).first()
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo nao encontrado")
    participantes = db.query(Usuario).filter(Usuario.id.in_(dados.participantes_ids)).all()
    if not participantes:
        raise HTTPException(status_code=400, detail="Nenhum participante selecionado")
    despesa = Despesa(
        descricao=dados.descricao,
        valor=dados.valor,
        data=dados.data,
        grupo_id=dados.grupo_id,
        pago_por_id=usuario.id,
    )
    db.add(despesa)
    db.flush()
    valor_por_pessoa = round(dados.valor / len(participantes), 2)
    for p in participantes:
        divisao = Divisao(
            despesa_id=despesa.id,
            usuario_id=p.id,
            valor_devido=valor_por_pessoa,
            pago=(p.id == usuario.id),
        )
        db.add(divisao)
    db.commit()
    db.refresh(despesa)
    return despesa

@app.get("/grupos/{grupo_id}/despesas", response_model=List[DespesaOut])
def listar_despesas(grupo_id: int, usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    return db.query(Despesa).filter(Despesa.grupo_id == grupo_id).all()

@app.get("/grupos/{grupo_id}/saldos")
def calcular_saldos(grupo_id: int, usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    grupo = db.query(Grupo).filter(Grupo.id == grupo_id).first()
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo nao encontrado")
    saldos = {}
    for p in grupo.participantes:
        saldos[p.id] = {"usuario_id": p.id, "nome": p.nome, "saldo": 0.0}
    despesas = db.query(Despesa).filter(Despesa.grupo_id == grupo_id).all()
    for despesa in despesas:
        saldos[despesa.pago_por_id]["saldo"] += despesa.valor
        for divisao in despesa.divisoes:
            if divisao.usuario_id in saldos:
                saldos[divisao.usuario_id]["saldo"] -= divisao.valor_devido
    return list(saldos.values())


# ── Frontend estático ─────────────────────────────────────────────────────────

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/manifest.json")
def serve_manifest():
    return FileResponse(os.path.join(FRONTEND_DIR, "manifest.json"))

@app.get("/sw.js")
def serve_sw():
    return FileResponse(os.path.join(FRONTEND_DIR, "sw.js"))

@app.get("/icon-192.png")
def serve_icon192():
    return FileResponse(os.path.join(FRONTEND_DIR, "icon-192.png"))

@app.get("/icon-512.png")
def serve_icon512():
    return FileResponse(os.path.join(FRONTEND_DIR, "icon-512.png"))
