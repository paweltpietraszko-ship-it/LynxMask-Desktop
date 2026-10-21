"""Independent retained reproducer. Run against exact backend path; synthetic data only."""
import sys
from dataclasses import dataclass
import pytest

@dataclass
class Ent:
    text:str
    label:str
    start:int
    end:int

@pytest.mark.parametrize('form',['Sp. z o.o.','S.A.','Sp. k.'])
def test_whole_legal_form_has_the_same_owner_as_fragment(form):
    from firma_context import legal_form_entities
    text='Wykonawca: BRZOZA '+form
    at=text.index(form)
    out=legal_form_entities(text,[Ent(form,'FIRMA',at,len(text))])
    assert [(x.text,x.label) for x in out]==[('BRZOZA '+form,'FIRMA')]

def test_whole_form_without_name_does_not_create_company():
    from firma_context import legal_form_entities
    text='Forma prawna: Sp. z o.o.'
    at=text.index('Sp.')
    assert legal_form_entities(text,[Ent(text[at:],'FIRMA',at,len(text))])==[]

@pytest.mark.parametrize('text,part',[('Jan A.','A.'),('A.','A.'),('Anna K. i Wspólnicy','K.')])
def test_initial_negative_control(text,part):
    from firma_context import legal_form_entities
    at=text.index(part);e=Ent(part,'OSOBA',at,at+len(part))
    assert legal_form_entities(text,[e])==[e]

if __name__=='__main__':
    sys.path.insert(0,sys.argv.pop(1))
    raise SystemExit(pytest.main([__file__,'-q','--tb=short','-p','no:cacheprovider']))

