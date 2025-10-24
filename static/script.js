// static/script.js
document.addEventListener("DOMContentLoaded", () => {
 const qsa = (s, el = document) => Array.from((el || document).querySelectorAll(s));


 // Auto-hide flashes after 3.8s
 setTimeout(() => {
   qsa(".flash").forEach(el => {
     el.style.transition = "opacity .35s, transform .35s";
     el.style.opacity = "0";
     el.style.transform = "translateY(-8px)";
     setTimeout(() => el.remove(), 420);
   });
 }, 3800);


 // data-confirm attribute
 qsa("[data-confirm]").forEach(el => {
   el.addEventListener("click", (e) => {
     const msg = el.dataset.confirm || "Are you sure?";
     if (!confirm(msg)) e.preventDefault();
   });
 });


 // Eye button toggles for password fields (SVG button, non-emoji)
 qsa(".eye-btn").forEach(btn => {
   btn.addEventListener("click", (e) => {
     e.preventDefault();
     const targetId = btn.dataset.target;
     const target = document.getElementById(targetId);
     if (!target) return;
     target.type = (target.type === "password") ? "text" : "password";
   });
 });


 // Show / hide both password inputs on register page via the 'pw-toggle-register' button
 const pwToggleReg = document.getElementById("pw-toggle-register");
 if (pwToggleReg) {
   pwToggleReg.addEventListener("click", () => {
     const p1 = document.getElementById("password");
     const p2 = document.getElementById("confirm");
     if (!p1 || !p2) return;
     const newType = p1.type === "password" ? "text" : "password";
     p1.type = p2.type = newType;
     pwToggleReg.textContent = newType === "text" ? "Hide Passwords" : "Show Passwords";
   });
 }


 // Basic form validation & highlighting for register form
 const registerForm = document.getElementById("registerForm");
 if (registerForm) {
   const first = document.getElementById("first_name");
   const middle = document.getElementById("middle_name");
   const last = document.getElementById("last_name");
   const dob = document.getElementById("dob");
   const age = document.getElementById("age");
   const contact = document.getElementById("contact");
   const email = document.getElementById("email");
   const username = document.getElementById("username");
   const pw = document.getElementById("password");
   const conf = document.getElementById("confirm");


   // set DOB constraints (1945-01-01 .. 2012-12-31)
   if (dob) {
     dob.min = "1945-01-01";
     dob.max = "2012-12-31";
     dob.addEventListener("change", () => {
       if (!dob.value) { age.value = ""; return; }
       const d = new Date(dob.value);
       const now = new Date();
       let a = now.getFullYear() - d.getFullYear();
       const m = now.getMonth() - d.getMonth();
       if (m < 0 || (m === 0 && now.getDate() < d.getDate())) a--;
       if (a < 13 || a > 80) {
         alert("Age must be between 13 and 80.");
         dob.value = "";
         age.value = "";
         dob.classList.add("invalid");
         setTimeout(()=>dob.classList.remove("invalid"),1600);
         return;
       }
       age.value = a;
     });
   }


   // contact input: only digits, max 11
   if (contact) {
     contact.addEventListener("input", () => {
       contact.value = contact.value.replace(/\D/g,'').slice(0,11);
     });
   }


   // client-side validation on submit
   registerForm.addEventListener("submit", (e) => {
     e.preventDefault();
     // helper
     const markInvalid = (el) => { el.classList.add("invalid"); el.focus(); setTimeout(()=>el.classList.remove("invalid"),2000); };
     // Names: letters + spaces, each word capitalized, 2-30
     const nameRE = /^[A-Z][a-z]+(?:\s[A-Z][a-z]+)*$/;
     if (!first.value || first.value.length < 2 || first.value.length > 30 || !nameRE.test(first.value)) { markInvalid(first); alert("First name must be 2-30 chars and each word capitalized."); return; }
     if (middle.value && (middle.value.length <2 || middle.value.length >30 || !nameRE.test(middle.value))) { markInvalid(middle); alert("Middle name must be 2-30 chars and capitalized."); return; }
     if (!last.value || last.value.length < 2 || last.value.length > 30 || !nameRE.test(last.value)) { markInvalid(last); alert("Last name must be 2-30 chars and each word capitalized."); return; }
     // dob already checked
     if (!contact.value || !/^09\d{9}$/.test(contact.value)) { markInvalid(contact); alert("Contact must be 11 digits and start with 09."); return; }
     // email basic & domain allowed
     const emailRE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
     if (!emailRE.test(email.value)) { markInvalid(email); alert("Invalid email address."); return; }
     const allowed = ["gmail.com","yahoo.com","outlook.com","hotmail.com","icloud.com"];
     const domain = email.value.split("@").pop().toLowerCase();
     if (!allowed.includes(domain)) { markInvalid(email); alert("Please use common domains: gmail, yahoo, outlook, hotmail, icloud."); return; }
     // username
     if (!/^[A-Za-z0-9_.\-@+]{3,30}$/.test(username.value)) { markInvalid(username); alert("Username invalid — 3–30; allowed . _ - @ +"); return; }
     // password strength
     if (!/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*\W).{8,}$/.test(pw.value)) { markInvalid(pw); alert("Password must be at least 8 chars and include upper, lower, number and symbol."); return; }
     if (pw.value !== conf.value) { markInvalid(conf); alert("Passwords do not match."); return; }
     // confirm
     if (!confirm("Create new account?")) return;
     registerForm.submit();
   });
 }


 // Profile page OTP handling and form prefill for provinces/cities/barangays
 const addressData = (function(){
   // minimal dataset for other provinces; Laguna fully populated (same as you asked)
   return {
     "Laguna": {
       "Calamba City": {"zip":"4027","barangays":["Bagong Kalsada","Banadero","Banlic","Barandal","Batino","Bubuyan","Bucal","Bunggo","Burol","Camaligan","Canlubang","Halang","Hornalan","Kay-Anlog","La Mesa","Laguerta","Lawa","Lecheria","Lingga","Looc","Mabato","Majada Labas","Makiling","Mapagong","Masili","Maunong","Mayapa","Paciano Rizal","Palingon","Palo-Alto","Pansol","Parian","Prinza","Punta","Puting Lupa","Real","Saimsim","Sampiruhan","San Cristobal","San Jose","San Juan","Sirang Lupa","Sucol","Turbina","Tulo","Ulango","Uwisan"]},
       "Santa Rosa City": {"zip":"4026","barangays":["Aplaya","Balibago","Caingin","Dila","Don Jose","Ibaba","Labas","Macabling","Malitlit","Malusak","Market Area","Pooc","Pulong Santa Cruz","Santo Domingo","Sinalhan","Tagapo"]},
       "Biñan City": {"zip":"4024","barangays":["Biñan (Poblacion)","Binitayan","Sto. Tomas (Poblacion)","Mamplasan","Mao","Sambera","Sto. Niño (Poblacion)","Ganado","Langkiwa","San Francisco (Halang)","San Antonio","San Jose","San Vicente","Sito de Gulod","Canlalay","Casile","Dela Paz","Gatid","Malaban","Platero","San Roque","Timbao","Tubigan","Zapote"]},
       "San Pedro City": {"zip":"4023","barangays":["Bagong Silang","Cuyab","Estrella","Landayan","Langgam","Laram","Mabini","Magsaysay","Maharlika","Narra","Pacita 1","Pacita 2","Poblacion","San Roque","San Vicente","Santo Niño","United Bayanihan"]},
       "Los Baños": {"zip":"4030","barangays":["Anos","Bagong Silang","Bambang","Batong Malake","Baybayin","Bayog","Lalakay","Maahas","Malinta","Mayondon","San Antonio","Tadlac","Timugan","Tuntungin-Putho"]},
       "Calauan": {"zip":"4012","barangays":["Imok","Balayhangin","Bangyas","Dayap","F. Manalo","Hanggan","Kalinawan","Lamot 1","Lamot 2","Lascano","Linga","Mabacan","Masiit","Poblacion 1","Poblacion 2","Poblacion 3","Poblacion 4"]},
       "Santa Cruz (Capital)": {"zip":"4009","barangays":["Bagumbayan","Gatid","J.P. Rizal (Poblacion)","Kansay","Labuin","Malinao","Oogong","Pagsawitan","Palasan","Pambijan (Poblacion)","Patimbao","Sampaguita (Poblacion)","San Jose","San Juan","San Lorenzo","San Pablo Norte","San Pablo Sur","Santa Cruz (Poblacion)"]},
       // ... add others as needed (kept minimal for speed)
     },
     "Cavite": {"Bacoor":{"zip":"4102","barangays":["Zapote","Niog","Aniban","Aplaya"]},"Imus":{"zip":"4103","barangays":["Poblacion","Anabu I","Anabu II"]}},
     "Batangas": {"Batangas City":{"zip":"4200","barangays":["Alangilan","Bolbok","Concepcion"]},"Lipa":{"zip":"4217","barangays":["Poblacion","Antipolo","Sabang"]}},
     "Rizal": {"Antipolo":{"zip":"1870","barangays":["San Roque","Dela Paz"]},"Cainta":{"zip":"1900","barangays":["San Andres","San Isidro"]}},
     "Quezon": {"Lucena":{"zip":"4301","barangays":["Poblacion I","Poblacion II"]},"Tayabas":{"zip":"4325","barangays":["Poblacion","San Roque"]}}
   };
 })();


 // populate province select(s)
 const populateProvinces = (selProv, selCity, selBrgy, selZip, preProv, preCity, preBrgy, preZip) => {
   selProv.innerHTML = '<option value="">Select</option>';
   Object.keys(addressData).sort((a,b) => a.localeCompare(b)).forEach(p => {
     const o = document.createElement('option'); o.value = p; o.textContent = p; selProv.appendChild(o);
   });
   // autoselect Laguna
   if (addressData['Laguna']) {
     selProv.value = preProv || 'Laguna';
     populateCities(selProv, selCity, selBrgy, selZip, preCity, preBrgy, preZip);
   }
 };
 const populateCities = (selProv, selCity, selBrgy, selZip, preCity, preBrgy, preZip) => {
   selCity.innerHTML = '<option value="">Select City / Municipality</option>';
   selBrgy.innerHTML = '<option value="">Select Barangay</option>';
   selZip.value = '';
   const p = selProv.value;
   if (!p || !addressData[p]) return;
   Object.keys(addressData[p]).sort((a,b) => a.localeCompare(b)).forEach(c => {
     const o = document.createElement('option'); o.value = c; o.textContent = c; selCity.appendChild(o);
   });
   if (preCity) selCity.value = preCity, populateBarangays(selProv, selCity, selBrgy, selZip, preBrgy, preZip);
 };
 const populateBarangays = (selProv, selCity, selBrgy, selZip, preBrgy, preZip) => {
   selBrgy.innerHTML = '<option value="">Select Barangay</option>';
   selZip.value = '';
   const p = selProv.value, c = selCity.value;
   if (!p || !c || !addressData[p] || !addressData[p][c]) return;
   (addressData[p][c].barangays || []).sort((a,b)=>a.localeCompare(b)).forEach(b => {
     const o = document.createElement('option'); o.value = b; o.textContent = b; selBrgy.appendChild(o);
   });
   if (addressData[p][c].zip) selZip.value = addressData[p][c].zip;
   if (preBrgy) selBrgy.value = preBrgy;
 };


 // hookup top-level register page selects
 const prov = document.getElementById('province');
 const city = document.getElementById('city');
 const brgy = document.getElementById('barangay');
 const zip = document.getElementById('zipcode');
 if (prov) {
   populateProvinces(prov, city, brgy, zip);
   prov.addEventListener('change', ()=> populateCities(prov, city, brgy, zip));
   city.addEventListener('change', ()=> populateBarangays(prov, city, brgy, zip));
 }


 // profile page selects (prefill using server values when present)
 const pfProv = document.getElementById('pf_province');
 const pfCity = document.getElementById('pf_city');
 const pfBrgy = document.getElementById('pf_barangay');
 const pfZip = document.getElementById('pf_zipcode');
 if (pfProv) {
   // server-provided values (if any) are embedded as option values in template; we read them
   const preProv = "{{ user.province|default('') }}".replace(/&quot;/g,'"').trim();
   const preCity = "{{ user.city|default('') }}".replace(/&quot;/g,'"').trim();
   const preBrgy = "{{ user.barangay|default('') }}".replace(/&quot;/g,'"').trim();
   const preZip = "{{ user.zipcode|default('') }}".replace(/&quot;/g,'"').trim();
   populateProvinces(pfProv, pfCity, pfBrgy, pfZip, preProv, preCity, preBrgy, preZip);
   pfProv.addEventListener('change', ()=> populateCities(pfProv, pfCity, pfBrgy, pfZip));
   pfCity.addEventListener('change', ()=> populateBarangays(pfProv, pfCity, pfBrgy, pfZip));
 }


 // profile OTP flow (AJAX) - Request OTP
 const requestOtpBtn = document.getElementById("requestOtpBtn");
 const otpBox = document.getElementById("otpBox");
 const otpInput = document.getElementById("otp_input");
 const otpCountdown = document.getElementById("otp_countdown");
 const verifyOtpBtn = document.getElementById("verifyOtpBtn");
 const cancelOtpBtn = document.getElementById("cancelOtpBtn");


 let otpTimer = null;
 function startOtpCountdown(seconds) {
   clearInterval(otpTimer);
   let s = parseInt(seconds,10);
   if (!s || s <= 0) { otpCountdown.textContent = ""; return; }
   otpBox.style.display = "block";
   const end = Date.now() + s*1000;
   otpTimer = setInterval(()=> {
     const rem = Math.max(0, Math.ceil((end - Date.now())/1000));
     otpCountdown.textContent = rem > 0 ? `${rem}s` : "Expired";
     if (rem <= 0) {
       clearInterval(otpTimer);
     }
   }, 300);
 }


 if (requestOtpBtn) {
   requestOtpBtn.addEventListener("click", async () => {
     // request OTP via POST
     const res = await fetch("{{ url_for('auth.request_profile_otp') }}", {method:"POST", headers:{'X-Requested-With':'XMLHttpRequest'}});
     if (!res.ok) {
       alert("Failed to request OTP (not logged in?).");
       return;
     }
     const data = await res.json();
     if (data.success) {
       // show OTP on-screen (demo mode) and countdown
       otpInput.value = data.otp || "";
       startOtpCountdown(data.expiry || 30);
       alert("OTP shown on screen (demo). It will expire in " + (data.expiry || 30) + " seconds.");
     } else {
       alert(data.msg || "Failed to request OTP.");
     }
   });
 }


 if (verifyOtpBtn) {
   verifyOtpBtn.addEventListener("click", async () => {
     const otpVal = otpInput.value.trim();
     const newPass = document.getElementById("new_pass").value.trim();
     const confirmPass = document.getElementById("confirm_pass").value.trim();
     if (!otpVal || !newPass || !confirmPass) { alert("Enter OTP and new password fields."); return; }
     if (newPass !== confirmPass) { alert("Passwords do not match."); return; }
     if (!/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*\W).{8,}$/.test(newPass)) { alert("Password must be at least 8 chars and include upper, lower, number and symbol."); return; }
     const form = new FormData();
     form.append('otp', otpVal);
     form.append('new_password', newPass);
     form.append('confirm', confirmPass);
     const res = await fetch("{{ url_for('auth.verify_profile_otp') }}", {method:"POST", body:form, headers:{'X-Requested-With':'XMLHttpRequest'}});
     const data = await res.json();
     if (data.success) {
       alert("Password updated successfully.");
       otpInput.value = ""; document.getElementById("new_pass").value = ""; document.getElementById("confirm_pass").value = "";
       otpBox.style.display = "none";
       otpCountdown.textContent = "";
     } else {
       alert(data.msg || "Failed to verify OTP.");
     }
   });
 }


 if (cancelOtpBtn) {
   cancelOtpBtn.addEventListener("click", ()=> { otpBox.style.display = "none"; otpCountdown.textContent = ""; otpInput.value = ""; document.getElementById("new_pass").value=""; document.getElementById("confirm_pass").value=""; });
 }


});
// Add confirmation for restore actions
document.addEventListener('DOMContentLoaded', function() {
    // Select all restore buttons and add confirmation
    const restoreButtons = document.querySelectorAll('a.btn-success[href*="restore_note"]');
    
    restoreButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const noteTitle = this.closest('.note-card').querySelector('h4').textContent;
            if (!confirm(`Are you sure you want to restore "${noteTitle}"?`)) {
                e.preventDefault();
            }
        });
    });
});
function validateEditForm(noteId) {
    const form = document.getElementById('editNoteForm' + noteId);
    const originalTitle = form.dataset.originalTitle;
    const originalContent = form.dataset.originalContent;
    const currentTitle = form.querySelector('input[name="title"]').value.trim();
    const currentContent = form.querySelector('textarea[name="content"]').value.trim();
    
    if (currentTitle === originalTitle && currentContent === originalContent) {
        alert('Error: No changes detected. Please make changes before saving.');
        return false;
    }
    
    if (!currentTitle) {
        alert('Error: Title cannot be empty.');
        return false;
    }
    
    return true;
}