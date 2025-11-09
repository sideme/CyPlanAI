from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Threat, ControlMapping

reasoning_bp = Blueprint('reasoning', __name__)


def score(likelihood: int, impact: int) -> int:
    likelihood = max(1, min(5, likelihood))
    impact = max(1, min(5, impact))
    return likelihood * impact


@reasoning_bp.route('/risk-score', methods=['POST'])
@jwt_required()
def risk_score():
    """Compute simple likelihood × impact scores and suggest mapped controls."""
    data = request.get_json() or {}
    items = data.get('threats', [])

    results = []
    for item in items:
        # Accept by name or id
        t = None
        if item.get('threatId'):
            t = Threat.query.filter_by(threatId=item['threatId']).first()
        elif item.get('name'):
            t = Threat.query.filter_by(name=item['name']).first()

        if not t:
            continue

        l = item.get('likelihood', t.likelihood or 2)
        i = item.get('impact', t.impact or 3)
        s = score(l, i)

        mappings = ControlMapping.query.filter_by(threatId=t.threatId).all()
        controls = []
        for m in mappings:
            c = m.control
            if not c:
                continue
            controls.append({
                'reference': c.reference,
                'title': c.title,
                'frameworkId': c.frameworkId,
                'category': c.category,
                'evidence_hint': m.evidence_hint,
            })

        results.append({
            'threat': t.to_dict(),
            'likelihood': l,
            'impact': i,
            'score': s,
            'recommended_controls': controls,
        })

    return jsonify({'results': results}), 200


