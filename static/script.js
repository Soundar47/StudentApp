const periods = 5;
const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

const subjectBody = document.getElementById("subjectBody");
const generatedSection = document.getElementById("generatedSection");
const tableBody = document.getElementById("tableBody");
const departmentSelect = document.getElementById("department");
const semesterSelect = document.getElementById("semester");
const sectionSelect = document.getElementById("section");
const facultyInput = document.getElementById("faculty");

function timetableKey() {
    return ["collegeTimetable", departmentSelect.value, semesterSelect.value, sectionSelect.value]
        .map(value => String(value).replace(/\s+/g, "_"))
        .join("_");
}

function escapeHtml(value) {
    const element = document.createElement("div");
    element.textContent = value;
    return element.innerHTML;
}

function subjectRow(subject = "New Subject", type = "Theory", weeklyPeriods = 1, labs = 0, position = "Auto", faculty = "Faculty") {
    const row = document.createElement("tr");
    row.innerHTML = `
        <td contenteditable="true">${escapeHtml(subject)}</td>
        <td><select class="subjectType"><option value="Theory">Theory</option><option value="Lab">Lab</option></select></td>
        <td><input type="number" min="0" value="${weeklyPeriods}"></td>
        <td><input type="number" min="0" value="${labs}"></td>
        <td><select class="labPosition"><option value="Auto">Auto</option><option value="First">P1-P3</option><option value="Last">P3-P5</option></select></td>
        <td contenteditable="true">${escapeHtml(faculty)}</td>
        <td><button type="button" class="deleteBtn">Delete</button></td>`;
    row.querySelector(".subjectType").value = type;
    row.querySelector(".labPosition").value = position;
    updateLabControls(row);
    return row;
}

function updateLabControls(row) {
    const isLab = row.querySelector(".subjectType").value === "Lab";
    const periodsInput = row.cells[2].querySelector("input");
    const labsInput = row.cells[3].querySelector("input");
    const position = row.querySelector(".labPosition");
    periodsInput.disabled = isLab;
    labsInput.disabled = !isLab;
    position.disabled = !isLab;
    if (isLab && Number(labsInput.value) === 0) labsInput.value = 1;
    if (!isLab) position.value = "Auto";
}

function getSubjects() {
    return [...subjectBody.querySelectorAll("tr")].map(row => ({
        subject: row.cells[0].innerText.trim(),
        type: row.querySelector(".subjectType").value,
        periods: Number(row.cells[2].querySelector("input").value) || 0,
        labs: Number(row.cells[3].querySelector("input").value) || 0,
        labPosition: row.querySelector(".labPosition").value,
        faculty: row.cells[5].innerText.trim()
    }));
}

function clearTable() {
    [...tableBody.rows].forEach(row => {
        for (let column = 1; column <= periods; column += 1) {
            row.cells[column].innerHTML = "";
            row.cells[column].classList.remove("lab");
            row.cells[column].contentEditable = "false";
        }
    });
}

function lessonHtml(subject, faculty) {
    return `<strong>${escapeHtml(subject)}</strong><br><small>${escapeHtml(faculty)}</small>`;
}

function shuffled(values) {
    return [...values].sort(() => Math.random() - 0.5);
}

function generateTimeTable() {
    const subjects = getSubjects();
    const invalid = subjects.find(item => !item.subject || !item.faculty);
    if (invalid) {
        alert("Enter a subject name and faculty for every row.");
        return;
    }

    const requiredSlots = subjects.reduce((total, item) => total + (item.type === "Lab" ? item.labs * 3 : item.periods), 0);
    if (requiredSlots > days.length * periods) {
        alert(`The selected subjects need ${requiredSlots} slots, but this timetable has only ${days.length * periods} slots.`);
        return;
    }

    const labSessions = subjects.flatMap(item =>
        item.type === "Lab" ? Array.from({ length: item.labs }, () => item) : []
    );
    if (labSessions.length > days.length) {
        alert("A maximum of six 3-period lab sessions can fit in this timetable.");
        return;
    }

    clearTable();
    const rows = [...tableBody.rows];
    const availableDays = shuffled(rows.map((_, index) => index));

    labSessions.forEach((lab, index) => {
        const row = rows[availableDays[index]];
        const starts = lab.labPosition === "First" ? [1] : lab.labPosition === "Last" ? [3] : shuffled([1, 3]);
        const start = starts[0];
        for (let column = start; column < start + 3; column += 1) {
            row.cells[column].innerHTML = lessonHtml(lab.subject, lab.faculty);
            row.cells[column].classList.add("lab");
        }
    });

    const remaining = subjects
        .filter(item => item.type === "Theory")
        .map(item => ({ ...item, remaining: item.periods }));

    rows.forEach(row => {
        let previous = "";
        for (let column = 1; column <= periods; column += 1) {
            if (row.cells[column].innerHTML) continue;
            const candidates = remaining.filter(item => item.remaining > 0 && item.subject !== previous);
            const pool = candidates.length ? candidates : remaining.filter(item => item.remaining > 0);
            if (!pool.length) continue;
            const highestCount = Math.max(...pool.map(item => item.remaining));
            const selected = shuffled(pool.filter(item => item.remaining === highestCount))[0];
            row.cells[column].innerHTML = lessonHtml(selected.subject, selected.faculty);
            selected.remaining -= 1;
            previous = selected.subject;
        }
    });

    generatedSection.style.display = "block";
}

function saveTimeTable() {
    const timetable = {
        department: departmentSelect.value,
        semester: semesterSelect.value,
        section: sectionSelect.value,
        faculty: facultyInput.value,
        table: [...tableBody.rows].map(row => [...row.cells].map(cell => cell.innerHTML))
    };
    localStorage.setItem(timetableKey(), JSON.stringify(timetable));
    lockTable();
    alert("Timetable saved for this department, semester, and section.");
}

function loadTimeTable() {
    const saved = JSON.parse(localStorage.getItem(timetableKey()) || "null");
    if (!saved) {
        generatedSection.style.display = "none";
        return;
    }
    saved.table.forEach((cells, rowIndex) => cells.forEach((html, columnIndex) => {
        if (tableBody.rows[rowIndex] && tableBody.rows[rowIndex].cells[columnIndex]) {
            tableBody.rows[rowIndex].cells[columnIndex].innerHTML = html;
        }
    }));
    facultyInput.value = saved.faculty || "";
    generatedSection.style.display = "block";
    lockTable();
}

function editTimeTable() {
    [...tableBody.rows].forEach(row => {
        for (let column = 1; column <= periods; column += 1) row.cells[column].contentEditable = "true";
    });
}

function lockTable() {
    tableBody.querySelectorAll("td").forEach((cell, index) => {
        if (index % (periods + 1) !== 0) cell.contentEditable = "false";
    });
}

function deleteTimeTable() {
    if (confirm("Delete the saved timetable for this class?")) {
        localStorage.removeItem(timetableKey());
        clearTable();
        generatedSection.style.display = "none";
    }
}

document.getElementById("addSubject").addEventListener("click", () => subjectBody.appendChild(subjectRow()));
document.getElementById("generate").addEventListener("click", generateTimeTable);
document.getElementById("rearrange").addEventListener("click", generateTimeTable);
document.getElementById("save").addEventListener("click", saveTimeTable);
document.getElementById("edit").addEventListener("click", editTimeTable);
document.getElementById("delete").addEventListener("click", deleteTimeTable);
document.addEventListener("click", event => {
    if (event.target.classList.contains("deleteBtn")) event.target.closest("tr").remove();
});
document.addEventListener("change", event => {
    if (event.target.classList.contains("subjectType")) updateLabControls(event.target.closest("tr"));
});
[departmentSelect, semesterSelect, sectionSelect].forEach(element => element.addEventListener("change", loadTimeTable));
subjectBody.querySelectorAll("tr").forEach(updateLabControls);
loadTimeTable();
