from flask import Blueprint, render_template, request, redirect, url_for, flash
from extensions import db
from .models import Lead
from .forms import QuoteForm

cad_bp = Blueprint("cad", __name__)

@cad_bp.route("/")
def home():
    form = QuoteForm()
    return render_template("home.html", form=form)

@cad_bp.route("/services")
def services():
    return render_template("services.html")

@cad_bp.route("/gallery")
def gallery():
    return render_template("gallery.html")

@cad_bp.route("/booking")
def booking():
    return render_template("booking.html")

@cad_bp.route("/quote", methods=["POST"])
def quote():
    form = QuoteForm()
    if form.validate_on_submit():
        lead = Lead(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            vehicle=form.vehicle.data,
            service=form.service.data,
            message=form.message.data,
        )
        db.session.add(lead)
        db.session.commit()
        flash("Thanks! We received your request and will reach out.", "success")
        return redirect(url_for("cad.home"))
    for field, errors in form.errors.items():
        for err in errors:
            flash(f"{field}: {err}", "danger")
    return redirect(url_for("cad.home"))
