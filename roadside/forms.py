
import json
import re

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import AssistanceRequest, Provider
from .utils import is_valid_coordinate

PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9\s\-]{8,18}$")


def validate_phone(value):
    value = (value or "").strip()
    if value and not PHONE_PATTERN.match(value):
        raise forms.ValidationError(
            "Enter a valid phone number (digits only, 9 to 19 characters)."
        )
    return value


# ==========================================
# TAMIL NADU DISTRICTS AND MAJOR CITIES
# ==========================================

TAMIL_NADU_CITIES = {
    "Ariyalur": ["Ariyalur", "Jayankondam", "Sendurai", "Andimadam"],
    "Chengalpattu": ["Chengalpattu", "Tambaram", "Pallavaram", "Chromepet", "Guduvanchery", "Maraimalai Nagar"],
    "Chennai": ["Chennai"],
    "Coimbatore": ["Coimbatore", "Pollachi", "Mettupalayam", "Valparai", "Annur", "Kinathukadavu"],
    "Cuddalore": ["Cuddalore", "Chidambaram", "Panruti", "Neyveli", "Virudhachalam", "Bhuvanagiri"],
    "Dharmapuri": ["Dharmapuri", "Palacode", "Harur", "Pennagaram", "Pappireddipatti"],
    "Dindigul": ["Dindigul", "Palani", "Kodaikanal", "Oddanchatram", "Nilakottai", "Vedasandur"],
    "Erode": ["Erode", "Gobichettipalayam", "Bhavani", "Perundurai", "Sathyamangalam", "Modakurichi"],
    "Kallakurichi": ["Kallakurichi", "Ulundurpet", "Sankarapuram", "Chinnasalem", "Tirukoilur"],
    "Kancheepuram": ["Kancheepuram", "Sriperumbudur", "Uthiramerur", "Walajabad", "Kundrathur"],
    "Kanniyakumari": ["Nagercoil", "Marthandam", "Kuzhithurai", "Colachel", "Padmanabhapuram", "Kanyakumari"],
    "Karur": ["Karur", "Kulithalai", "Aravakurichi", "Pallapatti", "Krishnarayapuram"],
    "Krishnagiri": ["Krishnagiri", "Hosur", "Denkanikottai", "Pochampalli", "Uthangarai"],
    "Madurai": ["Madurai", "Melur", "Usilampatti", "Thirumangalam", "Vadipatti", "Peraiyur"],
    "Mayiladuthurai": ["Mayiladuthurai", "Sirkazhi", "Tharangambadi", "Kuthalam"],
    "Nagapattinam": ["Nagapattinam", "Vedaranyam", "Kilvelur", "Thirukkuvalai"],
    "Namakkal": ["Namakkal", "Tiruchengode", "Rasipuram", "Paramathi Velur", "Kumarapalayam"],
    "The Nilgiris": ["Ooty", "Coonoor", "Kotagiri", "Gudalur", "Wellington"],
    "Perambalur": ["Perambalur", "Kunnam", "Veppanthattai", "Alathur"],
    "Pudukkottai": ["Pudukkottai", "Aranthangi", "Alangudi", "Iluppur", "Keeranur"],
    "Ramanathapuram": ["Ramanathapuram", "Rameswaram", "Paramakudi", "Kamuthi", "Mudukulathur", "Kilakarai"],
    "Ranipet": ["Ranipet", "Arcot", "Walajah", "Arakkonam", "Sholinghur", "Melvisharam"],
    "Salem": ["Salem", "Mettur", "Attur", "Edappadi", "Omalur", "Yercaud"],
    "Sivaganga": ["Sivaganga", "Karaikudi", "Devakottai", "Manamadurai", "Tirupathur"],
    "Tenkasi": ["Tenkasi", "Sankarankovil", "Kadayanallur", "Courtallam", "Shencottai", "Puliyangudi"],
    "Thanjavur": ["Thanjavur", "Kumbakonam", "Pattukkottai", "Orathanadu", "Thiruvaiyaru"],
    "Theni": ["Theni", "Periyakulam", "Bodinayakanur", "Cumbum", "Andipatti", "Uthamapalayam"],
    "Thoothukudi": ["Thoothukudi", "Kovilpatti", "Tiruchendur", "Sathankulam", "Ettayapuram", "Vilathikulam"],
    "Tiruchirappalli": ["Tiruchirappalli", "Srirangam", "Manapparai", "Thuraiyur", "Lalgudi", "Musiri"],
    "Tirunelveli": ["Tirunelveli", "Ambasamudram", "Nanguneri", "Cheranmahadevi", "Valliyur", "Radhapuram"],
    "Tirupathur": ["Tirupathur", "Vaniyambadi", "Ambur", "Natrampalli", "Jolarpet"],
    "Tiruppur": ["Tiruppur", "Dharapuram", "Udumalaipettai", "Palladam", "Avinashi", "Kangeyam"],
    "Tiruvallur": ["Tiruvallur", "Avadi", "Tiruttani", "Ponneri", "Gummidipoondi", "Poonamallee"],
    "Tiruvannamalai": ["Tiruvannamalai", "Arani", "Cheyyar", "Vandavasi", "Polur", "Chengam"],
    "Tiruvarur": ["Tiruvarur", "Mannargudi", "Thiruthuraipoondi", "Nannilam", "Needamangalam"],
    "Vellore": ["Vellore", "Katpadi", "Gudiyatham", "Pernambut", "Anaicut"],
    "Viluppuram": ["Viluppuram", "Tindivanam", "Gingee", "Vikravandi", "Marakkanam", "Kandachipuram"],
    "Virudhunagar": ["Virudhunagar", "Sivakasi", "Rajapalayam", "Sattur", "Aruppukkottai", "Srivilliputhur"],
}


# ==========================================
# REGISTRATION FORM
# ==========================================

class RegistrationForm(UserCreationForm):

    email = forms.EmailField(required=True)

    role = forms.ChoiceField(
        choices=[
            ("CUSTOMER", "Vehicle owner"),
            ("PROVIDER", "Service provider"),
        ]
    )

    business_name = forms.CharField(required=False, max_length=120)

    service_type = forms.ChoiceField(
        choices=Provider.SERVICE_TYPES,
        required=False
    )

    phone = forms.CharField(required=False, max_length=20)

    class Meta:
        model = User
        fields = [
            "username", "first_name", "last_name",
            "email", "password1", "password2"
        ]

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_phone(self):
        return validate_phone(self.cleaned_data.get("phone"))

    def clean(self):
        cleaned = super().clean()

        if cleaned.get("role") == "PROVIDER":
            for field in ("business_name", "service_type", "phone"):
                if not cleaned.get(field):
                    self.add_error(
                        field,
                        "This field is required for service providers."
                    )

        return cleaned


# ==========================================
# ASSISTANCE REQUEST FORM
# ==========================================

class AssistanceRequestForm(forms.ModelForm):

    state = forms.ChoiceField(
        choices=[("Tamil Nadu", "Tamil Nadu")],
        initial="Tamil Nadu",
        required=True
    )

    district = forms.ChoiceField(
        choices=[("", "Select District")],
        required=True
    )

    city = forms.ChoiceField(
        choices=[("", "Select City / Town")],
        required=True
    )

    class Meta:
        model = AssistanceRequest

        fields = [
            "service_needed",
            "vehicle",
            "issue_description",
            "phone",
            "state",
            "district",
            "city",
            "location_text",
            "latitude",
            "longitude",
        ]

        widgets = {
            "issue_description": forms.Textarea(attrs={"rows": 4}),
            "location_text": forms.TextInput(
                attrs={"placeholder": "Enter your street or area"}
            ),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["district"].choices = [
            ("", "Select District")
        ] + [
            (district, district)
            for district in TAMIL_NADU_CITIES
        ]

        self.fields["district"].widget.attrs["data-cities"] = json.dumps(
            TAMIL_NADU_CITIES
        )

        self.fields["latitude"].required = False
        self.fields["longitude"].required = False

        selected_district = (
            self.data.get(self.add_prefix("district"))
            if self.is_bound
            else self.initial.get("district", "")
        )

        if selected_district in TAMIL_NADU_CITIES:
            self.fields["city"].choices = [
                ("", "Select City / Town")
            ] + [
                (city, city)
                for city in TAMIL_NADU_CITIES[selected_district]
            ]


    def clean_phone(self):
        return validate_phone(self.cleaned_data.get("phone"))

    def clean(self):
        cleaned = super().clean()

        district = cleaned.get("district")
        city = cleaned.get("city")
        if district and city and city not in TAMIL_NADU_CITIES.get(district, []):
            self.add_error("city", "Select a city or town from the chosen district.")

        lat, lng = cleaned.get("latitude"), cleaned.get("longitude")
        if lat is None or lng is None:
            raise forms.ValidationError(
                "Please select your breakdown location using the GPS button "
                "or by clicking on the map."
            )
        if not is_valid_coordinate(lat, lng):
            raise forms.ValidationError(
                "The selected GPS location is invalid. Latitude must be between "
                "-90 and 90 and longitude between -180 and 180."
            )
        return cleaned


# ==========================================
# PROVIDER PROFILE FORM
# ==========================================

class ProviderProfileForm(forms.ModelForm):

    class Meta:
        model = Provider

        fields = [
            "business_name",
            "service_type",
            "phone",
            "description",
            "address",
            "latitude",
            "longitude",
            "is_available",
        ]

    def clean_phone(self):
        return validate_phone(self.cleaned_data.get("phone"))

    def clean(self):
        cleaned = super().clean()
        lat, lng = cleaned.get("latitude"), cleaned.get("longitude")

        if (lat is None) != (lng is None):
            raise forms.ValidationError(
                "Enter both latitude and longitude, or leave both empty."
            )
        if lat is not None and not is_valid_coordinate(lat, lng):
            raise forms.ValidationError(
                "Invalid GPS coordinates. Latitude must be between -90 and 90 "
                "and longitude between -180 and 180."
            )
        if cleaned.get("is_available") and lat is None:
            self.add_error(
                "is_available",
                "Add your GPS location before marking yourself available, "
                "otherwise you cannot receive nearby requests.",
            )
        return cleaned
