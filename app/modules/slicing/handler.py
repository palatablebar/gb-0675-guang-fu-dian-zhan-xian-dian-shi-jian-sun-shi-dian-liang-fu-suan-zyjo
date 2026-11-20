from fastapi import APIRouter, Request, Body
from app.engine import evaluate
from app.web import render
router=APIRouter()
@router.get('/slicing')
def page(request:Request):
    return render(request,'slicing')
@router.post('/api/slicing')
def calculate(payload:dict=Body(default={})):
    return evaluate(payload,until=3)
