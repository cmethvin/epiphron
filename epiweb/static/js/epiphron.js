function loadResults(id) {
    const checkResults = () => fetch(`/api/results/${id}`)
        .then(response => response.json())
        .then(data => {
            if (!data.done) {
                setTimeout(checkResults, 3000)
            } else {
                window.location.reload()
                console.log('done: ' + JSON.stringify(data))
            }
        })
    checkResults()
}