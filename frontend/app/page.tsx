"use client";
import "bootstrap/dist/css/bootstrap.min.css";
import React, { useState, useEffect, useRef } from "react";
import DisplayLists from "./components/displayLists";

export default function Home() {
  // Define your types for the data structure
  interface TaskData {
    term_list: { [key: string]: string };
    chapter_list: { [key: string]: string };
    sub_chapter_list: { [key: string]: string };
  }
  const mockTaskData = {
    term_list: {
      Thread: "A thread is a unit of execution within a process.",
      Process: "A process is a program in execution.",
    },
    chapter_list: {
      Introduction:
        "This chapter covers basic concepts of threading and processes.",
      "Advanced Topics":
        "This chapter covers advanced topics in process management.",
    },
    sub_chapter_list: {
      "Threads in Detail":
        "Details about how threads work and how they are managed by the OS.",
      "Process Isolation":
        "Discussion on how processes are isolated and managed in a multi-tasking environment.",
    },
  };
  const [taskId, setTaskId] = useState<string | null>();
  const [taskData, setTaskData] = useState<TaskData | null>(null);
  const [status, setStatus] = useState<string | null>("Waiting for Input...");
  const intervalRef = useRef<number | null>(null);

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const data = Object.fromEntries(form.entries());
    console.log(data);
    const response = await fetch("http://127.0.0.1:8000/tasks/create", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });
    const content = await response.json();
    console.log("API response:", content); // Make sure you see what you expect here
    setTaskId(content.taskid); // Corrected to the right property name
    console.log("Set Task ID:", content.taskid); //
  };

  // Fetch Task Data Function
  const fetchTaskData = async (taskId: string) => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/tasks/${taskId}`);
      if (!response.ok) {
        throw new Error("Task data could not be fetched.");
      }
      console.log("Task data fetched successfully. Status:", response.status);
      const responseData = await response.json();
      console.log("Fetched data:", responseData);

      // Assuming responseData.data contains the stringified JSON for each list
      const data = {
        term_list: JSON.parse(responseData.data.term_list || "{}"),
        chapter_list: JSON.parse(responseData.data.chapter_list || "{}"),
        sub_chapter_list: JSON.parse(
          responseData.data.sub_chapter_list || "{}"
        ),
      };
      const status = responseData.data.status || "";
      console.log("Status:", status);
      setTaskData(data);
      setStatus(status);
      console.log("Parsed data:", data);

      // Check if all lists have been populated
      if (status == "completed") {
        setTaskData(data);
        console.log("Task data is complete, stop polling.");
        if (intervalRef.current !== null) {
          clearInterval(intervalRef.current);
        }
      } else {
        console.log("Task data is not yet complete, continue polling.");
      }
    } catch (error) {
      console.error("Failed to fetch task data:", error);
      // Clear the interval using the ref
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current);
      }
    }
  };

  // ...

  // useEffect to poll for data once the taskID is set
  // useEffect to poll for data once the taskId is set
  useEffect(() => {
    if (taskId) {
      console.log("Polling for task data...");
      intervalRef.current = window.setInterval(() => {
        fetchTaskData(taskId);
      }, 1000);

      return () => {
        if (intervalRef.current !== null) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      };
    }
  }, [taskId]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      <div className="card">
        <form className="card-body" onSubmit={submit}>
          <div className="mb-3">
            <textarea name="url" className="form-control" placeholder="url" />
          </div>
          <button className="btn btn-primary">Submit</button>
        </form>
      </div>
      {status}

      <DisplayLists taskData={taskData} />
    </main>
  );
}
