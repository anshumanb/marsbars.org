module.exports = function(grunt) {

  grunt.initConfig({
    mustache_render: {
      all: {
        files: [
          {
            data: "data.json",
            template: "layout.mustache",
            dest: "index.html"
          }
        ]
      }
    }
  });

  grunt.loadNpmTasks('grunt-mustache-render');
};
