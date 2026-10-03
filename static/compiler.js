
const languageSelect = document.getElementById("language");
const codeEditor = document.getElementById("code");
const output = document.getElementById("output");
const runButton = document.getElementById("runButton");
const clearButton = document.getElementById("clearButton");
const previewSection = document.getElementById("htmlPreviewSection");
const preview = document.getElementById("htmlPreview");

const examples = {
    python: 'print("Welcome to NAT WORKS!")',
    javascript: 'console.log("Welcome to NAT WORKS!");',
    c: '#include <stdio.h>\nint main(void) {\n    printf("Welcome to NAT WORKS!\\n");\n    return 0;\n}',
    cpp: '#include <iostream>\nint main() {\n    std::cout << "Welcome to NAT WORKS!" << std::endl;\n    return 0;\n}',
    java: 'public class Main {\n    public static void main(String[] args) {\n        System.out.println("Welcome to NAT WORKS!");\n    }\n}',
    html: '<!DOCTYPE html>\n<html>\n<body>\n<h1>Hello NAT WORKS!</h1>\n<p>My first HTML page.</p>\n</body>\n</html>'
};

languageSelect.addEventListener("change", () => {
    codeEditor.value = examples[languageSelect.value];
    output.textContent = "Ready to run.";
    previewSection.hidden = true;
});

clearButton.addEventListener("click", () => {
    output.textContent = "";
});

runButton.addEventListener("click", async () => {
    const language = languageSelect.value;
    const source = codeEditor.value;

    if (language === "html") {
        preview.srcdoc = source;
        previewSection.hidden = false;
        output.textContent = "HTML loaded in the preview below.";
        return;
    }

    // This demo uses the public Piston API. API availability and
    // supported language versions may change. Do not send secrets.
    const runtimes = {
        python: "python",
        javascript: "javascript",
        c: "c",
        cpp: "c++",
        java: "java"
    };

    runButton.disabled = true;
    output.textContent = "Running code...";
    previewSection.hidden = true;

    try {
        const response = await fetch("https://emkc.org/api/v2/piston/execute", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                language: runtimes[language],
                version: "*",
                files: [{ name: "main", content: source }],
                stdin: ""
            })
        });

        if (!response.ok) {
            throw new Error("Compiler service returned HTTP " + response.status);
        }

        const result = await response.json();
        const run = result.run || {};
        output.textContent =
            (run.stdout || "") +
            (run.stderr ? "\nERROR:\n" + run.stderr : "") +
            (run.code !== undefined ? "\nExit code: " + run.code : "");

        if (!output.textContent.trim()) {
            output.textContent = "No output.";
        }
    } catch (error) {
        output.textContent =
            "Could not run the program. Check your internet connection " +
            "or try again later.\n" + error.message;
    } finally {
        runButton.disabled = false;
    }
});