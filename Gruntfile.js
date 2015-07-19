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
    },
    watch: {
      scripts: {
        files: ["data.json", "layout.mustache", "css/*.css"],
        tasks: ['mustache_render'],
        options: {
          spawn: true
        }
      }
    }
  });

  grunt.loadNpmTasks('grunt-mustache-render');
  grunt.loadNpmTasks('grunt-contrib-watch');
};
