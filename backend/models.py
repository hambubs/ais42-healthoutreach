"""SQLAlchemy models — dynamic operational state only.

Static datasets (12k villages, ~10.7k facilities) are served from in-memory
pandas (see optimizer.load_data); the SQLite DB stores only live state:
SOS alerts, dispatch jobs, optimized outposts and MMU breadcrumbs.
"""
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc)


class SosAlert(db.Model):
    __tablename__ = "sos_alerts"
    id = db.Column(db.Integer, primary_key=True)
    node_id = db.Column(db.String(50), nullable=False)
    village_id = db.Column(db.String(20))
    sos_type = db.Column(db.String(20), nullable=False, default="routine")  # routine|medicine|trauma|maternal
    priority = db.Column(db.String(10), default="normal")                    # normal|high|critical
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    source = db.Column(db.String(20), default="node")                       # node|hub_sync|demo
    status = db.Column(db.String(20), default="new")                        # new|dispatched|closed
    recommended_mode = db.Column(db.String(20))                             # rule-engine suggestion
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id, "node_id": self.node_id, "village_id": self.village_id,
            "sos_type": self.sos_type, "priority": self.priority,
            "lat": self.lat, "lon": self.lon, "source": self.source,
            "status": self.status, "recommended_mode": self.recommended_mode,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DispatchJob(db.Model):
    __tablename__ = "dispatch_jobs"
    id = db.Column(db.Integer, primary_key=True)
    alert_id = db.Column(db.Integer)          # FK SosAlert.id (nullable)
    outpost_id = db.Column(db.String(20))     # e.g. MMU-01
    mode = db.Column(db.String(20), nullable=False)  # ambulance|mmu_van|rider_2w|uav|outpost
    eta_min = db.Column(db.Float)
    handoff = db.Column(db.JSON)              # UAV partner handoff payload (mode=uav)
    status = db.Column(db.String(20), default="en_route")  # en_route|delivered|cancelled
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id, "alert_id": self.alert_id, "outpost_id": self.outpost_id,
            "mode": self.mode, "eta_min": self.eta_min, "handoff": self.handoff,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Outpost(db.Model):
    __tablename__ = "outposts"
    id = db.Column(db.Integer, primary_key=True)
    outpost_id = db.Column(db.String(20), unique=True, nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    anchor_district = db.Column(db.String(50))
    population_newly_covered = db.Column(db.Integer)
    villages = db.Column(db.JSON)            # assigned village ids
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            "outpost_id": self.outpost_id, "lat": self.lat, "lon": self.lon,
            "anchor_district": self.anchor_district,
            "population_newly_covered": self.population_newly_covered,
            "villages": self.villages or [],
        }


class MmuTrack(db.Model):
    __tablename__ = "mmu_track"
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id, "device_id": self.device_id, "lat": self.lat, "lon": self.lon,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
