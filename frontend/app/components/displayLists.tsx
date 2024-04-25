"use client";
import "bootstrap/dist/css/bootstrap.min.css";

interface TaskData {
  term_list: { [key: string]: any }; // Changed to 'any' to handle nested objects
  chapter_list: { [key: string]: any };
  sub_chapter_list: { [key: string]: any };
}

interface DisplayListsProps {
  taskData: TaskData | null;
}

const DisplayLists: React.FC<DisplayListsProps> = ({ taskData }) => {
  // console.log("Rendering DisplayLists, taskData:", taskData);

  if (!taskData) {
    return <p>No data available</p>;
  }

  // Helper function to render list items from an object
  const renderList = (dataObject: { [key: string]: string | undefined }) => {
    return (
      <ul>
        {Object.entries(dataObject).map(([key, value]) => (
          <li key={key} className="list-group-item">
            <strong>{key}:</strong> {value ? value : "No data"}
          </li>
        ))}
      </ul>
    );
  };

  return (
    <div className="container mt-4">
      <div className="row">
        {taskData ? (
          <>
            <div className="col-md-4">
              <h3>Chapters</h3>
              <ul className="list-group">
                {taskData.chapter_list ? (
                  renderList(taskData.chapter_list)
                ) : (
                  <p>Loading...</p>
                )}
              </ul>
            </div>
            <div className="col-md-4">
              <h3>Sub-Chapters</h3>
              <ul className="list-group">
                {taskData.sub_chapter_list ? (
                  renderList(taskData.sub_chapter_list)
                ) : (
                  <p>Loading...</p>
                )}
              </ul>
            </div>
            <div className="col-md-4">
              <h3>Terms</h3>
              <ul className="list-group">
                {taskData.term_list ? (
                  renderList(taskData.term_list)
                ) : (
                  <p>Loading...</p>
                )}
              </ul>
            </div>
          </>
        ) : (
          <p>No Task Data Available</p>
        )}
      </div>
    </div>
  );
};

export default DisplayLists;
