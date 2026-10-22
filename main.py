from pyscript import document
from js import window, Date
from pyodide.ffi import create_proxy

# -----------------------------
# CHARGING STATION SETTINGS
# -----------------------------

TOTAL_SLOTS = 20

PRICES = {
    30: 10,
    60: 20,
    120: 30
}

DURATION_NAMES = {
    30: "30 minutes",
    60: "1 hour",
    120: "2 hours"
}

selected_slot = "CH-01"
occupied = set()
bookings = []
_proxies = []
toast_timeout = None


# -----------------------------
# HELPER FUNCTIONS
# -----------------------------

def el(element_id):
    return document.getElementById(element_id)


def keep_proxy(callback):
    proxy = create_proxy(callback)
    _proxies.append(proxy)
    return proxy


def notify(message):
    global toast_timeout

    toast = el("toast")
    toast.textContent = message
    toast.classList.add("show")

    if toast_timeout is not None:
        window.clearTimeout(toast_timeout)

    toast_timeout = window.setTimeout(
        keep_proxy(lambda: toast.classList.remove("show")),
        3000
    )


def get_slot_id(number):
    return "CH-" + str(number).zfill(2)


# -----------------------------
# PAGE NAVIGATION
# -----------------------------

def show_page(page, button=None):
    for section in document.querySelectorAll(".page"):
        section.classList.remove("active")

    target = el(page)

    if target:
        target.classList.add("active")

    for item in document.querySelectorAll("nav button"):
        item.classList.remove("active")

    if button:
        button.classList.add("active")
    else:
        for item in document.querySelectorAll("nav button"):
            if item.getAttribute("data-page") == page:
                item.classList.add("active")
                break

    render_data()
    window.scrollTo({"top": 0, "behavior": "smooth"})


# -----------------------------
# CHARGING SLOT DISPLAY
# -----------------------------

def render_slots(container_id):
    container = el(container_id)
    container.innerHTML = ""

    for number in range(1, TOTAL_SLOTS + 1):
        slot_id = get_slot_id(number)
        busy = slot_id in occupied

        if busy:
            css_class = "busy"
            status = "Occupied"
        elif slot_id == selected_slot:
            css_class = "selected"
            status = "Available"
        else:
            css_class = "available"
            status = "Available"

        button = document.createElement("button")
        button.type = "button"
        button.className = "slot " + css_class
        button.disabled = busy

        button.innerHTML = (
            '<span style="font-size:22px">▣</span>'
            f'<strong>{slot_id}</strong>'
            f'<small><span class="dot">●</span> {status}</small>'
        )

        if not busy:
            button.addEventListener(
                "click",
                keep_proxy(
                    lambda event, sid=slot_id: select_slot(sid)
                )
            )

        container.appendChild(button)


def update_slot_options():
    select = el("bookingSlot")
    select.innerHTML = ""

    for number in range(1, TOTAL_SLOTS + 1):
        slot_id = get_slot_id(number)

        if slot_id not in occupied:
            option = document.createElement("option")
            option.value = slot_id
            option.textContent = slot_id + " - Available"
            select.appendChild(option)

    if selected_slot and selected_slot not in occupied:
        select.value = selected_slot
    elif select.options.length > 0:
        select.selectedIndex = 0

    available = TOTAL_SLOTS - len(occupied)

    el("bookingSlotCount").textContent = (
        "No slots available"
        if available == 0
        else f"{available} available"
    )

    confirm_button = el("confirmButton")
    confirm_button.disabled = available == 0

    confirm_button.textContent = (
        "No Slots Available"
        if available == 0
        else "Confirm Booking →"
    )


def select_slot(slot_id):
    global selected_slot

    if not slot_id or slot_id in occupied:
        notify("Please select an available charging slot.")
        return

    selected_slot = slot_id

    update_slot_options()
    render_slots("dashboardSlots")
    render_slots("bookingSlots")


# -----------------------------
# BOOKING PRICE
# -----------------------------

def update_price(event=None):
    duration = int(el("bookingDuration").value)
    el("bookingPrice").textContent = "₱" + str(PRICES[duration])


# -----------------------------
# CONFIRM BOOKING
# -----------------------------

def confirm_booking(event=None):
    global selected_slot

    slot_id = el("bookingSlot").value
    duration = int(el("bookingDuration").value)
    payment = el("bookingPayment").value

    if not slot_id:
        notify("No available slots. Please try again later.")
        return

    if slot_id in occupied:
        notify("This slot has already been booked. Choose another.")
        update_slot_options()
        render_slots("bookingSlots")
        return

    booking = {
        "slot": slot_id,
        "duration": DURATION_NAMES[duration],
        "minutes": duration,
        "amount": PRICES[duration],
        "payment": payment,
        "date": Date.new().toLocaleString(),
        "status": "Confirmed"
    }

    bookings.insert(0, booking)
    occupied.add(slot_id)

    selected_slot = ""

    for number in range(1, TOTAL_SLOTS + 1):
        candidate = get_slot_id(number)

        if candidate not in occupied:
            selected_slot = candidate
            break

    update_slot_options()
    render_slots("dashboardSlots")
    render_slots("bookingSlots")
    render_data()

    show_page("history")

    notify(
        f"Booking confirmed for {slot_id}! Demo payment only."
    )


# -----------------------------
# DASHBOARD AND BOOKING HISTORY
# -----------------------------

def render_data():
    total_spent = sum(
        item["amount"] for item in bookings
    )

    total_minutes = sum(
        item["minutes"] for item in bookings
    )

    el("statBookings").textContent = str(len(bookings))

    if total_minutes >= 60:
        el("statTime").textContent = (
            f"{total_minutes // 60} hr "
            f"{total_minutes % 60} min"
        )
    else:
        el("statTime").textContent = f"{total_minutes} min"

    el("statSpent").textContent = "₱" + str(total_spent)

    el("statAvailable").textContent = (
        f"{TOTAL_SLOTS - len(occupied)}/{TOTAL_SLOTS}"
    )

    if not bookings:
        el("recentActivity").innerHTML = (
            '<p style="color:var(--muted);font-size:13px;line-height:1.7">'
            "No bookings yet. Book your first charging slot "
            "to see your activity here.</p>"
        )

        el("historyRows").innerHTML = (
            '<p style="padding:22px 0;color:var(--muted)">'
            "No bookings yet. Your confirmed bookings "
            "will appear here.</p>"
        )

    else:
        recent_html = ""
        history_html = ""

        for booking in bookings[:4]:
            recent_html += (
                '<div class="activity">'
                '<div class="activity-icon">⚡</div>'
                '<div class="activity-info">'
                f'<strong>{booking["slot"]} · '
                f'{booking["duration"]}</strong>'
                f'<small>{booking["date"]}</small>'
                '</div>'
                f'<div class="activity-price">'
                f'₱{booking["amount"]}</div>'
                '</div>'
            )

        for booking in bookings:
            history_html += (
                '<div class="history-row">'
                '<span>'
                f'<strong>{booking["slot"]}</strong><br>'
                f'<small style="color:var(--muted)">'
                f'{booking["duration"]}</small>'
                '</span>'
                f'<span>{booking["date"]}</span>'
                f'<span><strong>₱{booking["amount"]}'
                '</strong></span>'
                '<span><span class="pill">'
                f'{booking["status"]}'
                '</span></span>'
                '</div>'
            )

        el("recentActivity").innerHTML = recent_html
        el("historyRows").innerHTML = history_html

    count = len(bookings)

    el("historyCount").textContent = (
        f"{count} booking"
        if count == 1
        else f"{count} bookings"
    )


# -----------------------------
# VIDEO AND MUSIC CONTROLS
# -----------------------------

def format_time(seconds):
    if not window.Number.isFinite(seconds):
        return "0:00"

    mins = int(seconds // 60)
    secs = int(seconds % 60)

    return f"{mins}:{str(secs).zfill(2)}"


def setup_audio():
    video = el("chargeHubAd")
    music = el("joyfulMusic")
    toggle = el("musicToggle")
    timer = el("adTimer")

    if not video or not music or not toggle or not timer:
        return

    music.muted = True
    music.volume = 0.40

    try:
        music.play()
    except Exception:
        pass

    def update_timer(event=None):
        timer.textContent = format_time(video.currentTime)

    def update_volume_icon():
        if music.muted or music.volume == 0:
            toggle.textContent = "🔇"
            toggle.setAttribute("aria-label", "Turn sound on")
        else:
            toggle.textContent = "🔊"
            toggle.setAttribute("aria-label", "Mute sound")

    def toggle_music(event=None):
        if music.muted:
            music.muted = False

            try:
                music.play()
            except Exception:
                pass
        else:
            music.muted = True

        update_volume_icon()

    toggle.addEventListener(
        "click",
        keep_proxy(toggle_music)
    )

    video.addEventListener(
        "timeupdate",
        keep_proxy(update_timer)
    )

    update_timer()
    update_volume_icon()


# -----------------------------
# BUTTON ACTIONS
# -----------------------------

def handle_action(event):
    action = event.currentTarget.getAttribute("data-action")

    if action in ("booking", "dashboard", "history"):
        show_page(action)

    elif action == "confirm-booking":
        confirm_booking()


for button in document.querySelectorAll("[data-action]"):
    button.addEventListener(
        "click",
        keep_proxy(handle_action)
    )


# -----------------------------
# NAVIGATION BUTTONS
# -----------------------------

for button in document.querySelectorAll("nav button[data-page]"):

    def nav_click(event):
        show_page(
            event.currentTarget.getAttribute("data-page"),
            event.currentTarget
        )

    button.addEventListener(
        "click",
        keep_proxy(nav_click)
    )


# -----------------------------
# INPUT EVENT LISTENERS
# -----------------------------

el("bookingDuration").addEventListener(
    "change",
    keep_proxy(update_price)
)

el("bookingSlot").addEventListener(
    "change",
    keep_proxy(
        lambda event: select_slot(el("bookingSlot").value)
    )
)


# -----------------------------
# INITIALIZE THE WEBSITE
# -----------------------------

update_slot_options()
render_slots("dashboardSlots")
render_slots("bookingSlots")
update_price()
render_data()
setup_audio()