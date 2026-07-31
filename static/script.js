/* ===========================================
   COLLEGE TIMETABLE MANAGEMENT SYSTEM
   PART 1
=========================================== */

// ===========================================
// CONSTANTS
// ===========================================

const periods = 5;

const days = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday"
];

// ===========================================
// ELEMENTS
// ===========================================

const addBtn = document.getElementById("addSubject");
const generateBtn = document.getElementById("generate");
const rearrangeBtn = document.getElementById("rearrange");
const subjectBody = document.getElementById("subjectBody");
const generatedSection = document.getElementById("generatedSection");

// Hide timetable initially
generatedSection.style.display = "none";

// ===========================================
// ADD SUBJECT
// ===========================================

addBtn.addEventListener("click", addSubjectRow);

function addSubjectRow() {

    const row = document.createElement("tr");

    row.innerHTML = `

        <td contenteditable="true">
            New Subject
        </td>

        <td>

            <select class="subjectType">

                <option value="Theory">
                    Theory
                </option>

                <option value="Lab">
                    Lab
                </option>

            </select>

        </td>

        <td>

            <input
                type="number"
                min="0"
                value="1">

        </td>

        <td>

            <input
                type="number"
                min="0"
                value="0">

        </td>

        <td>

            <select
                class="labPosition"
                disabled>

                <option value="Auto">
                    Auto
                </option>

                <option value="First">
                    P1-P3
                </option>

                <option value="Last">
                    P3-P5
                </option>

            </select>

        </td>

        <td contenteditable="true">
            Faculty
        </td>

        <td>

            <button
                class="deleteBtn">

                Delete

            </button>

        </td>

    `;

    subjectBody.appendChild(row);

}

// ===========================================
// DELETE SUBJECT
// ===========================================

document.addEventListener("click", function (e) {

    if (e.target.classList.contains("deleteBtn")) {

        if (confirm("Delete this subject?")) {

            e.target.closest("tr").remove();

        }

    }

});

// ===========================================
// ENABLE / DISABLE LAB POSITION
// ===========================================

document.addEventListener("change", function (e) {

    if (!e.target.classList.contains("subjectType"))
        return;

    const row =
        e.target.closest("tr");

    const type =
        e.target.value;

    const labPosition =
        row.querySelector(".labPosition");

    if (type === "Theory") {

        labPosition.disabled = true;

        labPosition.value = "Auto";

    }

    else {

        labPosition.disabled = false;

    }

});
/* ===========================================
   PART 2
   READ SUBJECTS & HELPER FUNCTIONS
=========================================== */

// ===========================================
// READ SUBJECT MASTER
// ===========================================

function getSubjects() {

    const rows =
        document.querySelectorAll("#subjectBody tr");

    let subjects = [];

    rows.forEach(row => {

        const subject =
            row.cells[0].innerText.trim();

        const type =
            row.cells[1]
            .querySelector("select").value;

        const periods =
            parseInt(
                row.cells[2]
                .querySelector("input").value
            ) || 0;

        const labs =
            parseInt(
                row.cells[3]
                .querySelector("input").value
            ) || 0;

        const labPosition =
            row.cells[4]
            .querySelector("select").value;

        const faculty =
            row.cells[5]
            .innerText.trim();

        subjects.push({

            subject,
            type,
            periods,
            labs,
            labPosition,
            faculty

        });

    });

    return subjects;

}

// ===========================================
// CLEAR TIMETABLE
// ===========================================

function clearTable() {

    const rows =
        document.querySelectorAll("#tableBody tr");

    rows.forEach(row => {

        for (let i = 1; i <= periods; i++) {

            row.cells[i].innerHTML = "";

            row.cells[i].classList.remove("lab");

        }

    });

}

// ===========================================
// SHUFFLE
// ===========================================

function shuffle(array) {

    for (let i = array.length - 1; i > 0; i--) {

        const j =
            Math.floor(
                Math.random() * (i + 1)
            );

        [array[i], array[j]] =
        [array[j], array[i]];

    }

}

// ===========================================
// GENERATE BUTTON
// ===========================================

generateBtn.addEventListener("click", function () {

    generateTimeTable();

    generatedSection.style.display = "block";

});

// ===========================================
// REARRANGE BUTTON
// ===========================================

rearrangeBtn.addEventListener("click", function () {

    generateTimeTable();

});

// ===========================================
// RANDOM EMPTY DAY
// ===========================================

function getAvailableDay(usedDays) {

    let available = [];

    for (let i = 0; i < days.length; i++) {

        if (!usedDays.includes(i)) {

            available.push(i);

        }

    }

    if (available.length === 0)
        return -1;

    return available[
        Math.floor(
            Math.random() *
            available.length
        )
    ];

}
/* ===========================================
   PART 3
   SMART TIMETABLE GENERATOR
=========================================== */

function generateTimeTable() {

    clearTable();

    const rows =
    document.querySelectorAll("#tableBody tr");

    const subjects =
    getSubjects();

    let theorySubjects = [];

    let labSubjects = [];

    // =======================================
    // CREATE SUBJECT LIST
    // =======================================

    subjects.forEach(sub => {

        if (sub.type === "Theory") {

            for (let i = 0; i < sub.periods; i++) {

                theorySubjects.push({

                    name: sub.subject,

                    faculty: sub.faculty

                });

            }

        }

        else {

            for (let i = 0; i < sub.labs; i++) {

                labSubjects.push({

                    name: sub.subject,

                    faculty: sub.faculty,

                    position: sub.labPosition

                });

            }

        }

    });

    shuffle(theorySubjects);

    shuffle(labSubjects);

    // =======================================
    // PLACE LABS
    // =======================================

    let usedDays = [];

    labSubjects.forEach(lab => {

        let day =
        getAvailableDay(usedDays);

        if (day == -1)
            return;

        usedDays.push(day);

        const row =
        rows[day];

        let start;

        if (lab.position == "First") {

            start = 1;

        }

        else if (lab.position == "Last") {

            start = 3;

        }

        else {

            start =
            Math.random() < 0.5
            ? 1
            : 3;

        }

        for (let i = start; i < start + 3; i++) {

            row.cells[i].innerHTML =

                `
                <strong>${lab.name}</strong>
                <br>
                <small>${lab.faculty}</small>
                `;

            row.cells[i]
            .classList.add("lab");

        }

    });

    // =======================================
    // FILL THEORY SUBJECTS
    // =======================================

    let pointer = 0;

    rows.forEach(row => {

        let previous = "";

        for (let i = 1; i <= periods; i++) {

            if (row.cells[i].innerHTML != "")
                continue;

            if (pointer >= theorySubjects.length) {

                shuffle(theorySubjects);

                pointer = 0;

            }

            let current =
            theorySubjects[pointer];

            // Avoid same subject twice continuously

            if (current.name == previous) {

                shuffle(theorySubjects);

                pointer = 0;

                current =
                theorySubjects[pointer];

            }

            row.cells[i].innerHTML =

                `
                ${current.name}
                <br>
                <small>${current.faculty}</small>
                `;

            previous =
            current.name;

            pointer++;

        }

    });

    alert(
        "Timetable Generated Successfully!"
    );

}
/* ===========================================
   PART 4A
   SAVE TIMETABLE
=========================================== */

// ===========================================
// BUTTON EVENTS
// ===========================================

document
.getElementById("save")
.addEventListener("click", saveTimeTable);

document
.getElementById("edit")
.addEventListener("click", editTimeTable);

document
.getElementById("delete")
.addEventListener("click", deleteTimeTable);

// ===========================================
// SAVE TIMETABLE
// ===========================================

function saveTimeTable() {

    const table = [];

    document
    .querySelectorAll("#tableBody tr")
    .forEach(row => {

        let rowData = [];

        row.querySelectorAll("td").forEach(cell => {

            rowData.push(cell.innerHTML);

        });

        table.push(rowData);

    });

    const timetable = {

        department:
        document.getElementById("department").value,

        semester:
        document.getElementById("semester").value,

        section:
        document.getElementById("section").value,

        faculty:
        document.getElementById("faculty").value,

        table: table

    };

    localStorage.setItem(

        "collegeTimetable",

        JSON.stringify(timetable)

    );

    lockTable();

    alert(

        "Timetable Saved Successfully."

    );

}

// ===========================================
// LOCK TABLE
// ===========================================

function lockTable() {

    document
    .querySelectorAll("#tableBody td")
    .forEach((cell, index) => {

        if (index % 6 != 0) {

            cell.contentEditable = false;

            cell.style.background = "#ffffff";

        }

    });

}